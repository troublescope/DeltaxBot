from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from app.helpers import ButtonMaker

# Initialize your Pyrogram client
app = Client(
    "my_bot",
    api_id=12345,
    api_hash="abcdefghijklmnopqrstuvwxyz",
    bot_token="123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
)


# Example 1: Simple menu with callback buttons
@app.on_message(filters.command("menu"))
async def menu_command(client: Client, message: Message):
    # Create a button maker instance
    buttons = ButtonMaker()

    # Add buttons to the first row
    buttons.add_button("Option 1", callback_data="opt_1")
    buttons.add_button("Option 2", callback_data="opt_2")

    # Add a new row and add more buttons
    buttons.add_row()
    buttons.add_button("Option 3", callback_data="opt_3")
    buttons.add_button("Option 4", callback_data="opt_4")

    # Method chaining example
    buttons.add_row().add_button("Help", callback_data="help")

    # Send message with the inline keyboard
    await message.reply_text("Please select an option:", reply_markup=buttons.build())


# Example 2: Navigation menu with URL and callback buttons
@app.on_message(filters.command("links"))
async def links_command(client: Client, message: Message):
    buttons = ButtonMaker()

    # First row with URL buttons
    buttons.add_button("Website", url="https://example.com")
    buttons.add_button("Documentation", url="https://docs.example.com")

    # Second row with navigation buttons
    buttons.add_row()
    buttons.add_button("Previous", callback_data="prev_page")
    buttons.add_button("Next", callback_data="next_page")

    # Adding button to specific row
    buttons.add_button("Contact Us", url="https://example.com/contact", row=0)

    await message.reply_text("Useful links:", reply_markup=buttons.build())


# Example 3: Dynamic grid of buttons
@app.on_message(filters.command("grid"))
async def grid_command(client: Client, message: Message):
    buttons = ButtonMaker()

    # Create a 3x3 grid of numbered buttons
    for row in range(3):
        for col in range(3):
            num = row * 3 + col + 1
            buttons.add_button(str(num), callback_data=f"grid_{num}", row=row)

    await message.reply_text("Select a number:", reply_markup=buttons.build())


# Example 4: Handling callback queries
@app.on_callback_query(filters.regex(r"^opt_"))
async def handle_option_callback(client: Client, callback_query: CallbackQuery):
    option = callback_query.data.split("_")[1]

    # Create new buttons for the selected option
    buttons = ButtonMaker()
    buttons.add_button("Go back", callback_data="back_to_menu")

    await callback_query.message.edit_text(
        f"You selected Option {option}. Here are the details...",
        reply_markup=buttons.build(),
    )


# Run the bot
if __name__ == "__main__":
    app.run()
