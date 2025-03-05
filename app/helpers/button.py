from typing import List, Optional

from pyrogram.types import (
    CallbackGame,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LoginUrl,
)


class ButtonMaker:
    """
    A utility class for easily creating and managing Pyrogram inline keyboard buttons.

    This class provides a fluent interface for creating multi-row inline keyboards
    with various button types supported by Pyrogram's InlineKeyboardButton.

    Attributes:
        keyboard (List[List[InlineKeyboardButton]]): A nested list representing rows and columns of buttons.

    Examples:
        Basic usage:
        ```python
        # Create a simple keyboard with URL and callback buttons
        buttons = ButtonMaker()
        buttons.add_button("Visit Website", url="https://example.com")
        buttons.add_row()
        buttons.add_button("Click Me", callback_data="button_clicked")
        keyboard = buttons.build()
        ```
    """

    def __init__(self):
        """
        Initialize a new ButtonMaker instance with an empty keyboard.
        """
        self.keyboard: List[List[InlineKeyboardButton]] = []

    def add_button(
        self,
        text: str,
        callback_data: Optional[str] = None,
        url: Optional[str] = None,
        login_url: Optional[LoginUrl] = None,
        switch_inline_query: Optional[str] = None,
        switch_inline_query_current_chat: Optional[str] = None,
        callback_game: Optional[CallbackGame] = None,
        user_id: Optional[int] = None,
        row: Optional[int] = None,
    ) -> "ButtonMaker":
        """
        Add a button to the keyboard with support for all parameters supported by InlineKeyboardButton.

        This method creates a new button with the provided parameters and adds it to the specified row.
        If no row is specified, the button is added to the last row. If there are no rows yet,
        a new row is created automatically.

        Args:
            text (str): The text displayed on the button.
            callback_data (Optional[str]): Data that will be sent when the button is pressed.
            url (Optional[str]): URL that will be opened when the button is pressed.
            login_url (Optional[LoginUrl]): An HTTP URL for user authentication.
            switch_inline_query (Optional[str]): String for triggering inline query in any chat.
            switch_inline_query_current_chat (Optional[str]): String for triggering inline query in current chat.
            callback_game (Optional[CallbackGame]): Callback game object for game buttons.
            user_id (Optional[int]): User ID who is allowed to press this button.
            row (Optional[int]): Row index (0-based). If not provided, button is added to the last row.

        Returns:
            ButtonMaker: The instance itself, allowing for method chaining.

        Note:
            You must provide exactly one of callback_data, url, login_url, switch_inline_query,
            switch_inline_query_current_chat, or callback_game according to Telegram Bot API requirements.
        """
        button_kwargs = {"text": text}
        if callback_data is not None:
            button_kwargs["callback_data"] = callback_data
        if url is not None:
            button_kwargs["url"] = url
        if login_url is not None:
            button_kwargs["login_url"] = login_url
        if switch_inline_query is not None:
            button_kwargs["switch_inline_query"] = switch_inline_query
        if switch_inline_query_current_chat is not None:
            button_kwargs["switch_inline_query_current_chat"] = (
                switch_inline_query_current_chat
            )
        if callback_game is not None:
            button_kwargs["callback_game"] = callback_game
        if user_id is not None:
            button_kwargs["user_id"] = user_id

        button = InlineKeyboardButton(**button_kwargs)

        # Ensure keyboard has at least one row
        if not self.keyboard:
            self.keyboard.append([])
        if row is None:
            self.keyboard[-1].append(button)
        else:
            while len(self.keyboard) <= row:
                self.keyboard.append([])
            self.keyboard[row].append(button)
        return self

    def add_row(self) -> "ButtonMaker":
        """
        Add a new row for buttons.

        This method adds an empty row to the keyboard, allowing for multi-row layouts.
        Subsequent calls to add_button() without a row parameter will add buttons to this new row.

        Returns:
            ButtonMaker: The instance itself, allowing for method chaining.
        """
        self.keyboard.append([])
        return self

    def build(self) -> InlineKeyboardMarkup:
        """
        Return the built InlineKeyboardMarkup object.

        This method finalizes the keyboard by cleaning up any empty rows
        and returning a Pyrogram InlineKeyboardMarkup object ready to be used.

        Returns:
            InlineKeyboardMarkup: The built keyboard markup object.

        Raises:
            ValueError: If the keyboard is completely empty.
        """
        if not self.keyboard or (len(self.keyboard) == 1 and not self.keyboard[0]):
            raise ValueError("Cannot build an empty keyboard")

        # Remove empty rows before building the keyboard
        cleaned_keyboard = [row for row in self.keyboard if row]
        return InlineKeyboardMarkup(cleaned_keyboard)
