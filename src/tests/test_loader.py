# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from radguestauth.loader import ImplLoader
from unittest import TestCase
from unittest.mock import patch, Mock, ANY, call
from radguestauth.auth import AuthHandler
from radguestauth.authhandlers.default import DefaultAuthHandler
from radguestauth.authhandlers.vlan import VlanAuthHandler


class ImplLoaderTest(TestCase):
    def test_nonexisting_class(self):
        loader = ImplLoader(object, str)
        result = loader.load("xyz")
        self.assertEqual(result, str)

    def test_invalid_name(self):
        loader = ImplLoader(object, str)
        result = loader.load("xyz!")
        self.assertEqual(result, str)

    def test_nonexisting_class_with_interface(self):
        loader = ImplLoader(AuthHandler, DefaultAuthHandler)
        result = loader.load("thisisnoauthhandler")
        self.assertEqual(result, DefaultAuthHandler)

    def test_load_impl(self):
        loader = ImplLoader(AuthHandler, DefaultAuthHandler)
        result = loader.load("Vlan")
        self.assertEqual(result, VlanAuthHandler)

    def test_load_impl_lowercase(self):
        loader = ImplLoader(AuthHandler, DefaultAuthHandler)
        result = loader.load("vlan")
        self.assertEqual(result, VlanAuthHandler)

    def test_load_impl_other_baseclass(self):
        loader = ImplLoader(object, DefaultAuthHandler)
        # Specifying another base class will result in a different,
        # non-existing namespace (radguestauth.objects).
        # The default implementation should be used.
        result = loader.load("Vlan")
        self.assertEqual(result, DefaultAuthHandler)

    def test_load_impl_subclass_check(self):
        loader = ImplLoader(str, DefaultAuthHandler)
        # explicitly specify module naming scheme, such that the class gets
        # loaded.
        # Because the VLAN handler is no subclass of str, the default
        # implementation should be returned.
        loader.base_module_name = 'authhandlers'
        loader.class_suffix = 'AuthHandler'
        result = loader.load("Vlan")
        self.assertEqual(result, DefaultAuthHandler)

        # with base_type object, the correct class should be used because
        # object is a valid supertye.
        loader.base_type = object
        result = loader.load("Vlan")
        self.assertEqual(result, VlanAuthHandler)
