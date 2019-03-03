# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from importlib import import_module
from inspect import getmembers

logger = logging.getLogger(__name__)


class ImplLoader(object):
    """
    Utility which dynamically loads implementations of base interfaces like
    Chat.

    The naming scheme for implementations of :base_type: is

    radguestauth.[lowercase name of :base_type: with appended 's']
        .[lowercase :impl_base_name:]
        .[impl_base_name][name of :base_type:]

    e.g. radguestauth.chats.udp.UdpChat for a load('Udp') call of a loader
    instantiated with base type 'Chat'.

    If desired, the parameters can be adjusted:
    - :base_module_name: is the part after radguestauth.
    - :class_suffix: is the last element
    """

    def __init__(self, base_type, default_impl):
        """
        Creates a loader for the given base_type (cf. class doc for details).

        :param base_type: Interface/abstract class like Chat or AuthHandler
        :param default_impl: Class (not instance!) of a default implementation
            to be used as fallback
        """
        base_name = base_type.__name__
        # if a base interface ending with 's' is introduced, probably
        # a custom base_module_name is necessary.
        self.base_module_name = base_name.lower() + 's'
        self.class_suffix = base_name
        self.base_type = base_type
        self.default_impl = default_impl

    def _load_class(self, impl_base_name):
        # avoid loading other modules with relative paths by replacing
        # dots in given item_name
        cleaned_name = impl_base_name.replace('.', '')
        submod_name = 'radguestauth.%s.%s' % (self.base_module_name,
                                              cleaned_name.lower())
        class_name = cleaned_name + self.class_suffix
        try:
            submod = import_module(submod_name)
            for name, impl in getmembers(submod):
                if name == class_name:
                    logger.debug('Successfully loaded %s.%s'
                                 % (submod_name, class_name))
                    return impl
        except ImportError:
            logger.error('Could not load %s.%s' % (submod_name, class_name),
                         exc_info=1)

        return None

    def load(self, impl_base_name):
        """
        Loads the class corresponding to impl_base_name with respect to the
        configured base_type setting of this loader instace.
        If no matching class is found, the specified default_impl is returned.

        Note that this does return a class, NOT an instance.

        :param impl_base_name: usually the first part of the class name (cf. docs
            of this class for details)
        :returns: the loaded class or default_impl
        """
        if impl_base_name.isidentifier():
            # ensure the first letter is uppercase
            formatted_name = impl_base_name[0].upper() + impl_base_name[1:]
            impl = self._load_class(formatted_name)
            if impl:
                if issubclass(impl, self.base_type):
                    return impl
                else:
                    logger.warn('%s is not a subclass of %s' %
                                (impl, self.base_type))
        else:
            logger.warn('Invalid name %s' % impl_base_name)

        logger.warn('Using default implementation %s.' % self.default_impl)
        return self.default_impl
