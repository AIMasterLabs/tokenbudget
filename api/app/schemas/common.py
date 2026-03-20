# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict = {}
