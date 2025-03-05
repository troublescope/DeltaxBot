# Import ButtonMaker class
from button_maker import ButtonMaker
from pyrogram import Client
from pyrogram.types import CallbackGame, LoginUrl, Message


# Example 1: Basic usage with URL and callback buttons
async def example_basic_keyboard(client: Client, message: Message):
    # Create buttons
    buttons = ButtonMaker()

    # Add a URL button
    buttons.add_button("Visit Website", url="https://example.com")

    # Add a callback button on the same row
    buttons.add_button("Help", callback_data="help_callback")

    # Add a new row
    buttons.add_row()

    # Add more buttons in the second row
    buttons.add_button("Settings", callback_data="settings")
    buttons.add_button("About", callback_data="about")

    # Build the keyboard
    keyboard = buttons.build()

    # Send a message with the keyboard
    await message.reply_text("Choose an option:", reply_markup=keyboard)


# Example 2: Using specific rows for organization
async def example_organized_keyboard(client: Client, message: Message):
    buttons = ButtonMaker()

    # Add buttons to specific rows
    buttons.add_button("Button 1", callback_data="btn1", row=0)
    buttons.add_button("Button 2", callback_data="btn2", row=0)

    buttons.add_button("Button 3", callback_data="btn3", row=1)

    buttons.add_button("Button 4", callback_data="btn4", row=2)
    buttons.add_button("Button 5", callback_data="btn5", row=2)
    buttons.add_button("Button 6", callback_data="btn6", row=2)

    keyboard = buttons.build()

    await message.reply_text("Organized keyboard example:", reply_markup=keyboard)


# Example 3: Using method chaining for cleaner code
async def example_method_chaining(client: Client, message: Message):
    keyboard = (
        ButtonMaker()
        .add_button("Page 1", callback_data="page_1")
        .add_button("Page 2", callback_data="page_2")
        .add_row()
        .add_button("Previous", callback_data="prev")
        .add_button("Next", callback_data="next")
        .add_row()
        .add_button("Cancel", callback_data="cancel")
        .build()
    )

    await message.reply_text("Method chaining example:", reply_markup=keyboard)


# Example 4: Using advanced button types
async def example_advanced_buttons(client: Client, message: Message):
    buttons = ButtonMaker()

    # URL button
    buttons.add_button("Website", url="https://example.com")
    buttons.add_row()

    # Login URL button
    login = LoginUrl(
        url="https://example.com/login",
        forward_text="Login to continue",
        bot_username="example_bot",
    )
    buttons.add_button("Login", login_url=login)
    buttons.add_row()

    # Switch inline query button
    buttons.add_button("Search", switch_inline_query="default search")
    buttons.add_row()

    # Switch inline query in current chat
    buttons.add_button("Search Here", switch_inline_query_current_chat="query")
    buttons.add_row()

    # Game button (if supported)
    buttons.add_button("Play Game", callback_game=CallbackGame())

    keyboard = buttons.build()

    await message.reply_text("Advanced buttons example:", reply_markup=keyboard)


# Example 5: Creating a paginated menu
async def create_paginated_menu(page: int, total_pages: int, items_per_page: int):
    buttons = ButtonMaker()

    # Add content buttons based on page number
    start_idx = (page - 1) * items_per_page
    for i in range(items_per_page):
        idx = start_idx + i
        buttons.add_button(f"Item {idx + 1}", callback_data=f"select_item_{idx}")
        if (i + 1) % 2 == 0:  # Add new row every 2 buttons
            buttons.add_row()

    # Navigation row
    buttons.add_row()
    if page > 1:
        buttons.add_button("◀️ Previous", callback_data=f"page_{page-1}")
    buttons.add_button(f"Page {page}/{total_pages}", callback_data="current_page")
    if page < total_pages:
        buttons.add_button("Next ▶️", callback_data=f"page_{page+1}")

    return buttons.build()


# How to use the paginated menu in a handler
async def example_pagination(client: Client, message: Message):
    keyboard = await create_paginated_menu(page=1, total_pages=5, items_per_page=6)

    await message.reply_text(
        "Paginated menu example (Page 1/5):", reply_markup=keyboard
    )
