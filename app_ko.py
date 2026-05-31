# -*- coding: utf-8 -*-
"""
R&S Entertainment Services — 오락기기 자산 추적·관리 시스템
한국어 진입점. 기본 언어가 한국어로 설정되어 부팅됩니다.
사이드바의 언어 토글로 English 전환도 가능합니다.
"""
from lib import app_main

app_main.run(default_lang="ko")
