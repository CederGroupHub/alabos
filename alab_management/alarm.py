"""The module to send alerts to the user via email or slack."""

import smtplib

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .config import AlabOSConfig


def format_message_to_codeblock(message: str) -> str:
    """
    The function takes a message and formats it as a code block.
    It is used to format tracebacks as code blocks in Slack.

    Args:
        message: The message to format (String). This is usually a traceback.

    Returns ------- formatted_message: The formatted message. This will be formatted into code block in slack if the
    message contains traceback, otherwise it will be the original message.
    """
    # Check if "Traceback (most recent call last):" is in the message
    # Split the message into lines
    lines = message.split("\n")

    # Find the index of the line that starts with "Traceback (most recent call last):"
    traceback_index = next(
        (
            i
            for i, line in enumerate(lines)
            if "Traceback (most recent call last):" in line
        ),
        None,
    )

    if traceback_index is not None:
        # Extract the traceback and the lines that follow it
        traceback_lines = lines[traceback_index:]

        # Join the traceback lines into a single string
        traceback_str = "\n".join(traceback_lines)

        # Format the traceback as a code block
        traceback_code = f"```{traceback_str}\n```"

        # Replace the original traceback lines with the formatted code block
        lines[traceback_index:] = [traceback_code]

        # Join the lines back into a single string
        formatted_message = "\n".join(lines)

    else:
        formatted_message = message
    return formatted_message


class Alarm:
    """A class to send alerts to the user via email or slack."""

    def __init__(
        self,
        email_receivers: list = None,
        email_sender: str = None,
        email_password: str = None,
        slack_bot_token: str = None,
        slack_channel_id: str = None,
    ):
        """
        Args:
            email_receivers: A list of email addresses to send the alert to.
            email_sender: The email address to send the alert from.
            email_password: The password for the email address to send the alert from.
            slack_bot_token: The slack bot token to send the alert from.
            slack_channel_id: The slack channel id to send the alert to.
        """
        self.sim_mode_flag = AlabOSConfig().is_sim_mode()
        self.email_alert = False
        self.slack_alert = False
        if email_receivers is not None:
            try:
                self.setup_email(email_sender, email_receivers, email_password)
                self.email_alert = True
            except:  # noqa: E722
                print("Email setup failed, please recheck config file")
        if slack_bot_token is not None:
            try:
                self.setup_slackbot(slack_bot_token, slack_channel_id)
                self.slack_alert = True
            except:  # noqa: E722
                print("Slackbot setup failed, please recheck config file")
        self.platforms = {"email": self.email_alert, "slack": self.slack_alert}

    def setup_email(
        self, email_receivers: list, email_sender: str, email_password: str
    ):
        """
        Try to setup email notification (called in __init__).

        Args:
            email_receivers: A list of email addresses to send the alert to.
            email_sender: The email address to send the alert from.
            email_password: The password for the email address to send the alert from.
        """
        try:
            self.email_receivers = email_receivers
            self.email_sender = email_sender
            self.email_password = email_password
            self.email_alert = True
            self.platforms = {"email": self.email_alert, "slack": self.slack_alert}
        except:  # noqa: E722
            print("Email setup failed, please recheck config file")

    def setup_slackbot(self, slack_bot_token: str, slack_channel_id: str):
        """
        Try to setup slackbot notification (called in __init__).

        Args:
            slack_bot_token: The token from slackbot app
            slack_channel_id: The slack channel id where the slackbot app is deployed.
        """
        try:
            self.slack_bot_token = slack_bot_token
            self.slack_channel_id = slack_channel_id
            self.slack_alert = True
            self.platforms = {"email": self.email_alert, "slack": self.slack_alert}
        except:  # noqa: E722
            print("Slackbot setup failed, please recheck config file")

    def alert(self, message: str, category: str):
        """
        Try to alert user in all platform in format of "Category: Message".

        Args:
            message: The message to print in the platform
            category: The category of the message.
        """
        if not self.sim_mode_flag:
            try:
                if self.platforms["email"]:
                    self.send_email(message, category)
                if self.platforms["slack"]:
                    self.send_slack_notification(message, category)
            except:  # noqa: E722
                if self.platforms["slack"]:
                    self.send_slack_notification(message, category)

    def send_email(self, message: str, category: str):
        """
        Send an email to the receiver email address with the exception and category.
        Category is the type of exception that occurred.
        Automatically use "Error" as category if the message contains traceback.

        Args:
            message: The message to print in the email
            category: The category of the message.
        """
        if "Traceback (most recent call last):" in message:
            category = "Error"
            # Automatically format to code block
            message = format_message_to_codeblock(message)
        self.message = f"Subject: {category}\n\n{message}"
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.email_sender, self.email_password)
            for receiver in self.email_receivers:
                server.sendmail(self.email_sender, receiver, self.message)

    def send_slack_notification(self, message: str, category: str):
        """
        Send a slack message to the receiver email address with the exception and category.
        Category is the type of exception that occurred.
        Automatically use "Error" as category if the message contains traceback.

        Args:
            message: The message to print in the email
            category: The category of the message.
        """
        if "Traceback (most recent call last):" in message:
            category = "Error"
            # Automatically format to code block
            message = format_message_to_codeblock(message)
        try:
            client = WebClient(token=self.slack_bot_token)
            client.chat_postMessage(
                channel=self.slack_channel_id, text=category + ": " + message
            )
        except SlackApiError as e:
            print(f"Error : {e}")
