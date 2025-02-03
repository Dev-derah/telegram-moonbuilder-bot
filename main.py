from datetime import datetime
from telegram import Message, Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from config import BOT_TOKEN, PACKAGES, WELCOME_MESSAGE, SOLANA_ADDRESS, ADMIN_USER_ID
from database import get_order_by_id, init_db, save_order, update_order_status,get_all_pending_orders
from utils import generate_payment_qr

async def set_bot_commands(application):
    """Set command menu for the bot."""
    commands = [
        BotCommand("start", "Start the bot 🚀"),
        BotCommand("approve", "Approve a pending order ✅ (Admin Only)"),
        BotCommand("complete", "Mark an order as completed 🎉"),
    ]
    await application.bot.set_my_commands(commands)

# Conversation states
CHOOSING_PACKAGE, ENTERING_DETAILS,CONFIRM_DETAILS, PAYMENT, PENDING_APPROVAL, WAITING_FOR_LINK = range(6)

WAITING_ORDER_ID, WAITING_WEBSITE_LINK = 6, 7

async def start(update: Update, context: CallbackContext):
    """Sends a welcome message and displays package options or approval button for admins."""
    user_name = update.message.from_user.full_name  # Get the user's full name
    user_id = update.message.from_user.id  # Get the user's Telegram ID
    
    # Check if the user is the admin
    if str(user_id) == str(ADMIN_USER_ID):
        # If the user is the admin, show the approval button for pending orders
        keyboard = [[InlineKeyboardButton("See Pending Orders", callback_data="see_pending_orders")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Hello Admin {user_name}! 👑\n\nYou can see pending orders below:", reply_markup=reply_markup, parse_mode="Markdown")
    else:
        # Otherwise, show the regular package options
        keyboard = [
            [InlineKeyboardButton(f"{pkg['title']} - {pkg['price']}", callback_data=pkg["callback_data"])]
            for pkg in PACKAGES
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Hello {user_name}! 👋\n\n" + WELCOME_MESSAGE, reply_markup=reply_markup, parse_mode="Markdown")

async def package_chosen(update: Update, context: CallbackContext):
    """Stores selected package and asks for coin details."""
    query = update.callback_query
    await query.answer()
    
    # Get the full package details from config
    selected_package = next(
        pkg for pkg in PACKAGES 
        if pkg['callback_data'] == query.data
    )
    
    # Store both key and title for later use
    context.user_data['package'] = {
        'key': selected_package['key'],
        'title': selected_package['title']
    }

    await query.message.reply_text(
        f"📦 You selected: {selected_package['title']}\n\n"
        "**Please copy the text below and fill it with your coin details.**",
        parse_mode="Markdown"
    )

    template_message = (
        "📝 *Please fill in the details below.* If any information is not available, just leave it empty.\n\n"
        "Coin Name: \n"
        "Coin Tokenomics (e.g., supply, max supply, etc.): \n\n"
        "Pump.fun link"
        "Social Links:\n"
        "Twitter: \n"
        "Discord: \n"
        "Telegram: \n"
        "Other Relevant Links: \n\n"
        "Once you're done, send the filled details in one message."
    )
    
    await query.message.reply_text(template_message)
    return ENTERING_DETAILS

async def receive_details(update: Update, context: CallbackContext):
    """Receives and stores coin details with validation."""
    try:
        # Validate message structure
        if not update.message.text.strip():
            await update.message.reply_text("❌ Please provide valid details")
            return ENTERING_DETAILS
        
        # Store details with timestamp
        user_input = update.message.text
        context.user_data['coin_details'] = {
            'text': user_input,
            'received_at': datetime.now().isoformat()
        }
        
        # Show confirmation message
        confirmation_text = (
            "📝 *Please confirm your details:*\n\n"
            f"{user_input}\n\n"
            "Choose an option below:"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data="details_confirmed"),
                InlineKeyboardButton("✏️ Edit", callback_data="edit_details")
            ]
        ]
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
        return CONFIRM_DETAILS
        
    except Exception as e:
        await update.message.reply_text("❌ Error saving details. Please try again.")
        return ConversationHandler.END

async def handle_confirmation(update: Update, context: CallbackContext):
    """Handles confirmation/edit choices"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "details_confirmed":
        await query.edit_message_reply_markup()  
        return await proceed_to_payment(query.message, context)
    else:
        await query.message.reply_text("✏️ Please send your updated details:")
        return ENTERING_DETAILS
    
async def proceed_to_payment(message: Message, context: CallbackContext):
    """Handles payment instructions (now accepts Message instead of Update)"""
    try:
        # Get package info
        package_info = context.user_data.get('package', {})
        package_key = package_info.get('key')
        
        # Validate package
        package = next(pkg for pkg in PACKAGES if pkg['key'] == package_key)
        sol_amount = float(package['price'].replace(" SOL", ""))
        
        # Generate QR with order info
        qr_code = generate_payment_qr(
            order_id=context.user_data.get('order_id', 'NEW'),
            amount=sol_amount
        )
        
        # Send payment instructions directly to the message
        await message.reply_photo(
            photo=qr_code,
            caption=f"💸 Send *{sol_amount} SOL* to:\n`{SOLANA_ADDRESS}`",
            parse_mode="Markdown"
        )
        
        # Create payment button
        keyboard = [[InlineKeyboardButton("✅ Payment Done", callback_data="payment_done")]]
        await message.reply_text(
            "Click below after payment:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return PAYMENT

    except StopIteration:
        await message.reply_text("❌ Invalid package. Use /start to begin again.")
        return ConversationHandler.END
    except Exception as e:
        await message.reply_text("🚨 Payment setup failed. Please try again.")
        return ConversationHandler.END

async def payment_confirmation(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    print('confirm payment confirmation')
    try:
        # Validate required data
        required_keys = ['package', 'coin_details']
        for key in required_keys:
            if key not in context.user_data:
                raise KeyError(f"Missing {key} in user data")
        
        # Get package details
        package_key = context.user_data['package'].get('key')
        package = next(pkg for pkg in PACKAGES if pkg['key'] == package_key)
        
        # Get coin details
        coin_details = context.user_data['coin_details']['text']
        
        # Save to database
        order_id = save_order(
            user_id=query.from_user.id,
            package=package['title'],
            details=coin_details,
            sol_amount=float(package['price'].replace(" SOL", ""))
        )
        
        # Confirm payment
        await query.edit_message_text(
            f"📦 Order #{order_id} Received!\n"
            "Status: Pending Approval\n"
            "We'll notify you once approved!"
        )
        

        print(query.from_user.username,query.from_user.first_name)
        # Notify admin
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"🆕 New Order {order_id}\n"
                f"Package: {package['title']}\n"
                f"User: @{query.from_user.username if query.from_user.username else query.from_user.first_name} (ID: {query.from_user.id})"
        )


    except KeyError as e:
        await query.message.reply_text(f"❌ Missing data: {str(e)}. Start over with /start")
    except Exception as e:
        await query.message.reply_text("❌ Payment confirmation failed. Contact support.")
        print(f"Payment error: {str(e)}")
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def see_pending_orders(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if str(query.from_user.id) != str(ADMIN_USER_ID):
        await query.message.reply_text("🚫 Unauthorized.")
        return

    pending_orders = get_all_pending_orders()
    
    if not pending_orders:
        await query.edit_message_text("🎉 No pending orders!")
        return
    
    keyboard = []

    for order in pending_orders:
        created_at = order['created_at']
        
        # 🛠️ Handle different types of timestamps
        if isinstance(created_at, float) or isinstance(created_at, int):
            # Convert Unix timestamp to datetime
            order_time = datetime.fromtimestamp(created_at)
        elif isinstance(created_at, str):
            try:
                order_time = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                order_time = datetime.fromisoformat(created_at)  # Try ISO format
        else:
            order_time = datetime.now()  # Fallback to current time if unknown format

        # Append button to the keyboard
        keyboard.append([
            InlineKeyboardButton(
                f"🆔 {order['id']} - {order_time.strftime('%d/%m %H:%M')}",
                callback_data=f"view_order_{order['id']}"
            )
        ])

    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    
    await query.edit_message_text(
        "📋 *Pending Orders*\n\n"
        "Click an order to view details:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
async def view_order(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    order_id = query.data.split("_")[-1]
    order = get_order_by_id(order_id)
    
    if not order:
        await query.message.reply_text("❌ Order not found")
        return
    
    # Format order details
    order_date = datetime.fromisoformat(order['created_at']).strftime('%Y-%m-%d %H:%M:%S')
    details = (
        f"📄 *Order Details* 🆔 `{order['id']}`\n"
        f"📅 *Date:* {order_date}\n"
        f"💼 *Package:* {order['package']}\n"
        f"👤 *User ID:* `{order['user_id']}`\n\n"
        "📝 *Coin Details:*\n"
        f"{order['coin_details']}"
    )
    
    # Create action buttons
    keyboard = [
        [InlineKeyboardButton("✅ Approve Payment", callback_data=f"approve_{order_id}")],
        [InlineKeyboardButton("🔙 Back to Orders", callback_data="see_pending_orders")]
    ]
    
    await query.edit_message_text(
        details,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def approve_order(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    order_id = query.data.split("_")[-1]
    order = get_order_by_id(order_id)
    
    if not order:
        await query.message.reply_text("❌ Order not found")
        return
    
    # Generate website ID (MLW-0001 format)
    website_id = f"MLW-{int(order_id):04d}"
    update_order_status(order_id, "approved", website_id)
    
    # Notify admin
    await query.edit_message_text(
        f"✅ *Order Approved!*\n\n"
        f"🆔 Website ID: `{website_id}`\n"
        f"📅 Due Date: {datetime.now().strftime('%Y-%m-%d 23:59:00')}",
        parse_mode="Markdown"
    )
    
    # Notify user
    await context.bot.send_message(
        chat_id=order['user_id'],
        text=f"🎉 *Payment Recieved!*\n\n"
            f"🆔 Your Website ID: `{website_id}`\n"
            f"⏳ Your website will be ready within 24 hours!\n\n"
            f"📅 Expected completion: {datetime.now().strftime('%Y-%m-%d 23:59:00')}",
        parse_mode="Markdown"
    )

async def complete_order(update: Update, context: CallbackContext):
    print(f"Admin {update.effective_user.id} starting completion")
    if str(update.effective_user.id) != str(ADMIN_USER_ID):
        await update.message.reply_text("🚫 Administrator only command")
        return ConversationHandler.END
        
    await update.message.reply_text("📝 Enter the Order ID to complete:")
    return WAITING_ORDER_ID
async def receive_order_id(update: Update, context: CallbackContext):
    print("Admin receive_order_id triggered")
    order_id = update.message.text.strip()
    
    if not order_id.isdigit():
        await update.message.reply_text("❌ Invalid Order ID. Only numbers allowed.")
        return WAITING_ORDER_ID

    try:
        order = get_order_by_id(int(order_id))
        if not order:
            await update.message.reply_text("❌ Order not found. Try again:")
            return WAITING_ORDER_ID
            
        context.user_data['completing_order'] = order_id
        await update.message.reply_text("🌐 Now send the website URL:")
        return WAITING_WEBSITE_LINK

    except Exception as e:
        print(f"Order ID error: {str(e)}")
        await update.message.reply_text("❌ Database error. Try again.")
        return WAITING_ORDER_ID
    
async def receive_website_link(update: Update, context: CallbackContext):
    """Finalizes order completion and notifies user"""
    order_id = context.user_data['completing_order']
    website_url = update.message.text
    
    try:
        # First validate order ID is numeric
        if not order_id.isdigit():
            raise ValueError("Invalid Order ID format")

        order_id = int(order_id)
        
        # Update database using the complete_order function
        from database import complete_order, get_user_id_by_order_id
        
        if not complete_order(order_id, website_url):
            raise ValueError("Failed to update database")

        # Get user ID from order
        user_id = get_user_id_by_order_id(order_id)
        if not user_id:
            raise ValueError("User not found for this order")

        # Notify user
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🚀 Your website is ready!\n\n"
                 f"🌐 {website_url}\n\n"
                 f"Thank you for choosing MoonBuilder!"
        )

        # Confirm to admin
        await update.message.reply_text(
            f"✅ Order {order_id} completed!\n"
            f"User has been notified."
        )

    except ValueError as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    except Exception as e:
        await update.message.reply_text("❌ Critical error. Check logs.")
        print(f"Completion error: {str(e)}")
    
    context.user_data.clear()
    return ConversationHandler.END
async def cancel(update: Update, context: CallbackContext):
    """Cancels any ongoing operation"""
    await update.message.reply_text("❌ Operation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END
def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('complete', complete_order)],
        states={
            WAITING_ORDER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order_id)],
            WAITING_WEBSITE_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_website_link)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(admin_conv_handler)
    
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(package_chosen, pattern="basic_package|pro_package|custom_package"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_details))
    application.add_handler(CallbackQueryHandler(handle_confirmation, pattern="^(details_confirmed|edit_details)$"))
    application.add_handler(CallbackQueryHandler(payment_confirmation, pattern="^payment_done$"))
    application.add_handler(CallbackQueryHandler(see_pending_orders, pattern="^see_pending_orders$"))
    application.add_handler(CallbackQueryHandler(view_order, pattern="^view_order_"))
    application.add_handler(CallbackQueryHandler(approve_order, pattern="^approve_"))
    application.add_handler(CallbackQueryHandler(start, pattern="^admin_back$"))



    application.run_polling()

if __name__ == '__main__':
    main()
