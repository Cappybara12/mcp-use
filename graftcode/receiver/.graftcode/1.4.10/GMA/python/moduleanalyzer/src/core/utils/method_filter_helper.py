from __future__ import annotations

from typing import Optional
import re

from moduleanalyzer.src.core.utils.type_filter_helper import TypeFilterHelper


class MethodFilterHelper:
  @staticmethod
  def matches_filter(
    method_name: str,
    method_filter: Optional[str],
    type_full_name: Optional[str] = None,
  ) -> bool:
    if not method_filter or not method_filter.strip():
      return True

    patterns = [
      p.strip()
      for p in method_filter.split(",")
      if p and p.strip()
    ]
    if not patterns:
      return True

    for pattern in patterns:
      if TypeFilterHelper._matches_wildcard_pattern(method_name, pattern):
        return True
      if type_full_name and TypeFilterHelper._matches_wildcard_pattern(
        f"{type_full_name}.{method_name}", pattern
      ):
        return True

    return False
