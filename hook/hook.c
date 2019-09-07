/*
 * Copyright (c) Nokia 2018. All rights reserved.
 *
 * Author: 
 * Email: nokia-sbell.com
 */
#define _GNU_SOURCE
#include <string.h>
#include <libgen.h>
#include <errno.h>
#include <fcntl.h>
#include <libgen.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define TARGET_CONFIG_FILE_SUFFIX ".target"
#define LOG_CONFIG_FILE "hooklog.conf"

#ifdef LOCAL_CONFIG
#include "local_config.h"
#endif

#ifndef LOCK_FILE
#define LOCK_FILE "/tmp/hooklogging.lck"
#endif

#undef TEST_LOCK

void fprint_string_escape(FILE *file, const char *str) {
	for (const char *p = str; *p != '\0'; p++) {
		switch (*p) {
			case '"':
				fputs("\\\"", file);
				break;
			case '\\':
				fputs("\\\\", file);
				break;
			case '\b':
				fputs("\\b", file);
				break;
			case '\f':
				fputs("\\f", file);
				break;
			case '\n':
				fputs("\\n", file);
				break;
			case '\r':
				fputs("\\r", file);
				break;
			case '\t':
				fputs("\\t", file);
				break;
			default:
				if (*p >= 0x00 && *p <= 0x1f) {
					int c = *p;
					fprintf(file, "\\u%04x", c);
				} else {
					putc(*p, file);
				}
		}
	}
}

int main(int argc, char **argv, char **envp) {
	int i;
	int ret;
	FILE *ptrFile;

	// get hook program path
	char *exePath = malloc(PATH_MAX);
	ret = readlink("/proc/self/exe", exePath, PATH_MAX);
	if (ret <= 0) {
		printf("[HOOK] Error readlink(\"/proc/self/exe\") return value: %d\n", ret);
		exit(1);
	}
	exePath[ret] = '\0';
	char *exeBaseName = basename(exePath);
	int exeBaseNameLength = strlen(exeBaseName);
	char *tmpExePath = malloc(ret + 1);
	strcpy(tmpExePath, exePath);
	char *exeDirPath = dirname(tmpExePath);
	int exeDirPathLength = strlen(exeDirPath);

#ifdef PRINT_TO_TERMINAL
	// get terminal width
	struct winsize stWinSize;
    ioctl(STDOUT_FILENO, TIOCGWINSZ, &stWinSize);
    int winWidth = stWinSize.ws_col - 7;

	printf("[HOOK] ");
	i = winWidth;
	while (i--) {
		printf("=");
	}
	printf("\n");
#endif

	// get log config
	char *logConfigFile;
	if (exeDirPath[exeDirPathLength - 1] == '/') {
		logConfigFile = malloc(exeDirPathLength + sizeof(LOG_CONFIG_FILE));
		strcpy(logConfigFile, exeDirPath);
		strcpy(logConfigFile + exeDirPathLength, LOG_CONFIG_FILE);
	} else {
		logConfigFile = malloc(exeDirPathLength + sizeof(LOG_CONFIG_FILE) + 1);
		strcpy(logConfigFile, exeDirPath);
		logConfigFile[exeDirPathLength] = '/';
		strcpy(logConfigFile + exeDirPathLength + 1, LOG_CONFIG_FILE);
	}
	ptrFile = fopen(logConfigFile, "r");
	if (ptrFile == NULL) {
		printf("[HOOK] Error open %s file\n", logConfigFile);
		exit(1);
	}
	char *logFilePath = NULL;
	size_t logFilePathSize;
	int logFilePathLength = getline(&logFilePath, &logFilePathSize, ptrFile);
	fclose(ptrFile);
	if (logFilePathLength == -1) {
		printf("[HOOK] Error get log file from config\n");
		exit(1);
	}
	while (logFilePath[logFilePathLength - 1] == '\n' || logFilePath[logFilePathLength - 1] == '\r') {
		logFilePath[logFilePathLength - 1] = '\0';
		logFilePathLength--;
	}

	// get hook target config
	char *targetConfigFile;
	if (exeDirPath[exeDirPathLength - 1] == '/') {
		targetConfigFile = malloc(exeDirPathLength + exeBaseNameLength + sizeof(TARGET_CONFIG_FILE_SUFFIX));
		strcpy(targetConfigFile, exeDirPath);
		strcpy(targetConfigFile + exeDirPathLength, exeBaseName);
		strcpy(targetConfigFile + exeDirPathLength + exeBaseNameLength, TARGET_CONFIG_FILE_SUFFIX);
	} else {
		targetConfigFile = malloc(exeDirPathLength + exeBaseNameLength + sizeof(TARGET_CONFIG_FILE_SUFFIX) + 1);
		strcpy(targetConfigFile, exeDirPath);
		targetConfigFile[exeDirPathLength] = '/';
		strcpy(targetConfigFile + exeDirPathLength + 1, exeBaseName);
		strcpy(targetConfigFile + exeDirPathLength + exeBaseNameLength + 1, TARGET_CONFIG_FILE_SUFFIX);
	}
	ptrFile = fopen(targetConfigFile, "r");
	if (ptrFile == NULL) {
		printf("[HOOK] Error open %s file\n", targetConfigFile);
		exit(1);
	}
	char *targetPath = NULL;
	size_t targetPathSize;
	int targetPathLength = getline(&targetPath, &targetPathSize, ptrFile);
	fclose(ptrFile);
	if (targetPathLength == -1) {
		printf("[HOOK] Error get target program from config\n");
		exit(1);
	}
	while (targetPath[targetPathLength - 1] == '\n' || targetPath[targetPathLength - 1] == '\r') {
		targetPath[targetPathLength - 1] = '\0';
		targetPathLength--;
	}

	// lock and open log file
	int logLockFd = open(LOCK_FILE, O_CREAT | O_RDWR, 0666);
	if (logLockFd < 0) {
		printf("[HOOK] Error open %s file\n", LOCK_FILE);
		printf("[HOOK] errno: %d\n", errno);
		exit(1);
	}
	if (flock(logLockFd, LOCK_EX) < 0) {
		printf("[HOOK] Error locking %s file\n", LOCK_FILE);
		printf("[HOOK] errno: %d\n", errno);
		exit(1);
	}
	FILE *ptrLogFile = fopen(logFilePath, "a");
	if (ptrLogFile == NULL) {
		printf("[HOOK] Error open %s file\n", logFilePath);
		exit(1);
	}
	if (ftell(ptrLogFile) > 0) {
		fprintf(ptrLogFile, "\n");
	}



	fprintf(ptrLogFile, "{\"hookProg\":\"");
	fprint_string_escape(ptrLogFile, exePath);
	fprintf(ptrLogFile, "\",\"hookedProg\":\"");
	fprint_string_escape(ptrLogFile, targetPath);
	fprintf(ptrLogFile, "\"");
#ifdef PRINT_TO_TERMINAL
	printf("[HOOK] Hook Path   : %s\n", exePath);
	printf("[HOOK] Hooked Prog : %s\n", targetPath);
#endif

	// count envs
	int envCount = 0;
	while (envp[envCount] != NULL) envCount++;
	char **env = malloc((envCount + 1) * sizeof(char *));

	// make a copy of envs
	fprintf(ptrLogFile, ",\"envs\":[");
	char *envModify = malloc(targetPathLength + 3);
	envModify[0] = '_';
	envModify[1] = '=';
	strcpy(envModify + 2, targetPath);
	for (i = 0; i < envCount; i++) {
		env[i] = envp[i];
		// change `_` env value
		if (env[i][0] == '_' && env[i][1] == '=') {
			// allocate new string memory
			env[i] = envModify;
		}
		if (i > 0) {
			fprintf(ptrLogFile, ",");
		}
		fprintf(ptrLogFile, "\"");
		fprint_string_escape(ptrLogFile, env[i]);
		fprintf(ptrLogFile, "\"");
#ifdef PRINT_TO_TERMINAL
		printf("[HOOK] env[%4d] = : %s\n", i, env[i]);
#endif
	}
	env[envCount] = NULL;
	fprintf(ptrLogFile, "]");

	// get working dir
	char *workingDir = malloc(PATH_MAX);
	if (getcwd(workingDir, PATH_MAX) == NULL) {
		printf("[HOOK] Error getcwd() return value\n");
		exit(1);
	}
	fprintf(ptrLogFile, ",\"cwd\":\"");
	fprint_string_escape(ptrLogFile, workingDir);
	fprintf(ptrLogFile, "\"");
#ifdef PRINT_TO_TERMINAL
	printf("[HOOK] Working Dir : %s\n", workingDir);
#endif

	// print command
	char **parm = malloc((argc + 1) * sizeof(char *));
	fprintf(ptrLogFile, ",\"cmd\":[");
#ifdef PRINT_TO_TERMINAL
	printf("[HOOK] Command     :");
#endif
	for (i = 0; i < argc; i++) {
		parm[i] = argv[i];
		if (i > 0) {
			fprintf(ptrLogFile, ",");
		}
		fprintf(ptrLogFile, "\"");
		fprint_string_escape(ptrLogFile, argv[i]);
		fprintf(ptrLogFile, "\"");
#ifdef PRINT_TO_TERMINAL
		printf(" %s", argv[i]);
#endif
	}
	parm[argc] = NULL;
	// change command line base name
	parm[0] = targetPath;
	fprintf(ptrLogFile, "]}");
#ifdef PRINT_TO_TERMINAL
	printf("\n");

	printf("[HOOK] ");
	i = winWidth;
	while (i--) {
		printf("=");
	}
	printf("\n");
#endif

#ifdef TEST_LOCK
	sleep(5);
#endif

	// close log file and unlock
	fclose(ptrLogFile);
	flock(logLockFd, LOCK_UN);
	close(logLockFd);

	free(exePath);
	free(tmpExePath);
	free(logConfigFile);
	free(targetConfigFile);
	free(workingDir);
	free(logFilePath);

	// transfer to target program
	ret = execve(targetPath, parm, env);

	printf("[HOOK] Error execve() status: %d\n", ret);
	printf("[HOOK] targetPath is: %s\n", targetPath);
	printf("[HOOK] errno: %d\n", errno);

	free(targetPath);
	free(env);
	free(envModify);
	free(parm);

	exit(ret);
}

