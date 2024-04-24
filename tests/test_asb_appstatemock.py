# SPDX-License-Identifier: MPL-2.0
import pytest

import appstatemock
import asb_testing


@pytest.fixture
def asb():
    return appstatemock.AppStateMock().asb

globals().update(asb_testing.generate_tests('appstatemock'))
