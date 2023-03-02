import smtplib
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def format_message_to_codeblock(message):
    # Check if "Traceback (most recent call last):" is in the message
    # Split the message into lines
    lines = message.split("\n")

    # Find the index of the line that starts with "Traceback (most recent call last):"
    traceback_index = next((i for i, line in enumerate(lines) if "Traceback (most recent call last):" in line), None)

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

class Alarm(object):
    def __init__(self, 
    email_receivers = None, 
    email_sender = None, 
    email_password = None,
    slack_bot_token = None,
    slack_channel = None
    ):
        self.email_alert = False
        self.slack_alert = False
        if email_receivers is not None:
            try:
                self.setup_email(email_sender, email_receivers, email_password)
                self.email_alert=True
            except:
                print("Email setup failed, please recheck config file")
        if slack_bot_token is not None:
            try:
                self.setup_slack(slack_bot_token, slack_channel)
                self.slack_alert=True
            except:
                print("Slackbot setup failed, please recheck config file")
        self.platforms = {"email": self.email_alert, "slack": self.slack_alert}
    
    def setup_email(self, email_receivers, email_sender, email_password):
        try:
            self.email_receivers = email_receivers
            self.email_sender = email_sender
            self.email_password = email_password
            self.email_alert=True
            self.platforms = {"email": self.email_alert, "slack": self.slack_alert}
        except:
            print("Email setup failed, please recheck config file")
    
    def setup_slackbot(self, slack_bot_token, slack_channel):
        try:
            self.slack_bot_token = slack_bot_token
            self.slack_channel = slack_channel
            self.slack_alert=True
            self.platforms = {"email": self.email_alert, "slack": self.slack_alert}
        except:
            print("Slackbot setup failed, please recheck config file")

    def alert(self,message,category):
        try:
            if self.platforms["email"]:
                self.send_email(message,category)
            if self.platforms["slack"]:
                self.send_slack_notification(message,category)
        except:
            if self.platforms["slack"]:
                self.send_slack_notification(message,category)

    def send_email(self, message, category):
        """
        Sends an email to the receiver email address with the exception and category.
        Category is the type of exception that occured.
        Example:
            send_email(Exception, "Emergency")
            send_email(Exception, "Warning, program continues")
        """
        self.message = f"Subject: {category}\n\n{message}"
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.email_sender, self.email_password)
            for receiver in self.email_receivers:
                server.sendmail(self.email_sender, receiver, self.message)
    
    def send_slack_notification(self, message, category):
        if "Traceback (most recent call last):" in message:
            category = "Error"
            # Automatically format to code block
            message=format_message_to_codeblock(message)
        try:
            client = WebClient(token=self.slack_bot_token)
            response = client.chat_postMessage(
                channel=self.slack_channel,
                text=category+": "+message
            )
            # print(response)
        except SlackApiError as e:
            print("Error : {}".format(e))

