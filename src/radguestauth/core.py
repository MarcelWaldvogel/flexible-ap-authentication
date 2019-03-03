# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time
import logging
import radguestauth.auth as auth
from radguestauth.users.usermanager import UserManager
from radguestauth.users.storage import UserIdentifier, UserData
from radguestauth.chatctl import ChatController
from radguestauth.authhandlers.default import DefaultAuthHandler
from radguestauth.loader import ImplLoader


# See https://www.iana.org/assignments/eap-numbers/eap-numbers.xhtml
EAP_TYPE_PEAP = 25
EAP_TYPE_MS_EAP_AUTH = 26
EAP_TYPE_MSCHAP_2 = 29
EAP_TYPE_PWD = 52


logger = logging.getLogger(__name__)


class GuestAuthCore(object):
    def __init__(self):
        self._user_manager = UserManager()
        self._config = dict()
        # AuthHandler and ChatController get dynamically loaded in startup()
        self._auth_handler = None
        self._chat_controller = None
        self._last_device = None
        self._last_session = None
        self._last_request_eap_pwd = False

    @staticmethod
    def get_eap_type(items_dict):
        """
        Returns the EAP-Message's type field as integer, or -1 if unavailable
        """
        msg = items_dict.get('EAP-Message', '')
        # message string starts with 0x, then followed by 4 octets for code,
        # identifier and length (8 hex digits). The type is 1 octet, so in
        # total we need 12 digits.
        # See RFC 3748, section 4.
        result = -1
        if len(msg) >= 12:
            try:
                result = int(msg[10:12], 16)
            except ValueError:
                pass

        return result

    @staticmethod
    def skip_eap_message(items_dict):
        """
        Indicates whether to ignore the EAP message stored in the respective
        field of items_dict.

        :returns: True if the message should be skipped
        """
        eap_type = GuestAuthCore.get_eap_type(items_dict)
        # Skip all messages except the supported authentication methods.
        # If there is no EAP Message, it should not be skipped (-1).
        return eap_type not in [
            -1, EAP_TYPE_PEAP, EAP_TYPE_MS_EAP_AUTH, EAP_TYPE_MSCHAP_2,
            EAP_TYPE_PWD
        ]

    def _add_post_auth_session_timeout(self, user_id, post_auth_dict):
        """
        Adds the Session-Timeout attribute to a dict prepared by the
        AuthHandler in post_auth if the user is known and has valid_until set.

        :param user_id: The UserIdentifier containing the post_auth call
            attributes
        :param post_auth_dict: A dict to be returned in post_auth, usually
            prepared by the AuthHandler. Can also be None.
        :returns: None if post_auth_dict was none, otherwise the given dict
            with the timeout attribute added.
        """
        stored_user = self._user_manager.find(user_id.name)

        if (stored_user == user_id and stored_user.user_data
                and stored_user.user_data.valid_until):
            user_valid = stored_user.user_data.valid_until
            # add 10 seconds to ensure the timeout is expired when
            # disconnecting
            session_timeout = user_valid - time.time() + 10

            if session_timeout > 0:
                logger.debug('Setting post_auth timeout %s for %s'
                             % (session_timeout, user_id.name))
                if not post_auth_dict:
                    post_auth_dict = dict()
                post_auth_dict['reply:Session-Timeout'] = session_timeout

        return post_auth_dict

    def startup(self, config):
        self._config = config
        # Dynamically load AuthHandler
        auth_loader = ImplLoader(auth.AuthHandler, DefaultAuthHandler)
        auth_impl = auth_loader.load(config.get('auth_handler',
                                                'Default'))
        self._auth_handler = auth_impl()
        self._auth_handler.start(self._config)
        # Initialize ChatController
        self._chat_controller = ChatController(self._user_manager,
                                               self._auth_handler)
        self._chat_controller.start(self._config)
        logger.info('radguestauth core started.')

    def authorize(self, items):
        username = items.get('User-Name')
        calling_id = items.get('Calling-Station-Id')
        acct_session = items.get('Acct-Session-Id', '')
        keys = items.keys()

        # remember attributes for EAP-PWD requests, as the inner tunnel value
        # has only the username set.
        if GuestAuthCore.get_eap_type(items) == EAP_TYPE_PWD:
            # EAP-PWD: set flag for following inner request
            self._last_request_eap_pwd = True
            self._last_device = calling_id
            self._last_session = acct_session
        elif self._last_request_eap_pwd and not calling_id:
            # EAP-PWD inner request: restore attributes from previous request
            calling_id = self._last_device
            acct_session = self._last_session
            self._last_device = None
            self._last_session = None

        if 'EAP-Message' in keys and 'FreeRADIUS-Proxied-To' not in keys:
            # skip outer EAP requests
            return (auth.NO_OP, None)

        if ('FreeRADIUS-Proxied-To' in keys
                and GuestAuthCore.skip_eap_message(items)):
            # EAP methods may use multiple inner messages.
            # Skip all messages except the ones specifying the authentication
            # method (such as PEAP or MSCHAPv2).
            return (auth.NO_OP, None)

        if username and calling_id:
            # reset EAP-PWD flag
            self._last_request_eap_pwd = False
            user_id = UserIdentifier(username, calling_id)
            state = self._user_manager.may_join(user_id)

            if state == UserData.JOIN_STATE_ALLOWED:
                # look up full user object with data
                user_id = self._user_manager.find(username)
                logger.debug('authorize called for user %s (ALLOWED)'
                             % username)
            elif state == UserData.JOIN_STATE_WAITING:
                # The user is the request user. Load the request to get the
                # password
                user_id = self._user_manager.get_request()
            elif state == UserData.JOIN_STATE_NEW:
                # always reject if another request is pending
                if self._user_manager.is_request_pending():
                    logger.info('Rejecting new user %s due to pending request'
                                % username)
                    return (auth.REJECT, None)
                # add request and notify host if successful
                if self._user_manager.add_request(user_id):
                    self._chat_controller.notify_join(user_id)
                    # load request user object with password attribute set
                    user_id = self._user_manager.get_request()
                    # state changes to WAITING now.
                    state = UserData.JOIN_STATE_WAITING
                else:
                    logger.warn('Failed to add request for %s', username)
                    # reject user without calling handler if something went
                    # wrong.
                    return (auth.REJECT, None)

            return self._auth_handler.handle_user_state(user_id, state,
                                                        acct_session)

        return (auth.REJECT, None)

    def post_auth(self, items):
        username = items.get('User-Name')
        calling_id = items.get('Calling-Station-Id')
        if username and calling_id:
            user_id = UserIdentifier(username, calling_id)
            acct_session = items.get('Acct-Session-Id', '')

            data = self._auth_handler.on_post_auth(user_id, acct_session)
            return self._add_post_auth_session_timeout(user_id, data)

        return None

    def drop_expired_users(self):
        """
        This is intended to be called e.g. via a nightly cron job.

        Usually, users get disconnected via session timeout or if the login
        number is exceeded. However, the entries in the UserManager and
        possible whitelist entries in AuthHandler can be present after a
        timeout if the user doesn't join again.

        Even though these users won't get connectivity if they join again at
        a later time, removing old entries regularly makes it easier for the
        host to keep track of current guests.

        To avoid long-standing requests, the request also gets removed.
        """
        expired = self._user_manager.get_expired_users()
        for user in expired:
            # call AuthHandler such that the user gets disconnected if needed
            self._auth_handler.on_host_deny(user)
            self._user_manager.remove(user)
            logger.info('Dropped expired user %s' % user.name)

        if self._user_manager.is_request_pending():
            self._auth_handler.on_host_deny(self._user_manager.get_request())
            self._user_manager.finish_request()
            logger.info('Removed ongoing request during drop_expired_users')

    def shutdown(self):
        try:
            self._chat_controller.stop()
            self._auth_handler.shutdown()
        except AttributeError as exc:
            logger.error(
                'Failed to shutdown. Likely, this occured because'
                + ' initialization went wrong. (%s)' % exc
            )
