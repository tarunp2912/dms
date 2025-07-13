# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

# import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class UnitTestDMSS3Settings(UnitTestCase):
    """
    Unit tests for DMSS3Settings.
    Use this class for testing individual functions and methods.
    """

    pass


class IntegrationTestDMSS3Settings(IntegrationTestCase):
    """
    Integration tests for DMSS3Settings.
    Use this class for testing interactions between multiple components.
    """

    pass
