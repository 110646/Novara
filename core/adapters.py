from allauth.account.adapter import DefaultAccountAdapter

class NoLoginMessageAdapter(DefaultAccountAdapter):
    def add_message(self, request, level, message_template, message_context=None, extra_tags=''):
        # Suppress all messages from Allauth (like "Successfully signed in")
        if message_template == 'account/messages/logged_in.txt':
            return  # Do nothing for the login message
        super().add_message(request, level, message_template, message_context, extra_tags)
