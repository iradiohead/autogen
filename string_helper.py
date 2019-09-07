#!/usr/bin/env python3

##
# Copyright (c) Nokia 2018. All rights reserved.
#
# Author: Zhou, Shiyu (NSB - CN/Hangzhou)
# Email: shiyu.zhou@nokia-sbell.com
#

import string
import random


def id_generator(size=6, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))
