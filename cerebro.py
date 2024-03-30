import logging
import os
from download_file import download_file_func
from openai  import OpenAI
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import sqlite3
from datetime import datetime
import prompts
import secrets_cerebro

# Variáveis de ambiente
TELEGRAM_API_KEY = secrets_cerebro.TELEGRAM_API_KEY
MY_CHAT_ID = secrets_cerebro.MY_CHAT_ID
TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

logger = logging.getLogger(__name__)

start_brainstorm = False
activate_visualiza = False

# Menus
IDEA_MENU = "<b>Ideia identificada!</b>\nVocê gostaria de fazer um brainstorm dessa ideia?"

SIM_BUTTON = "Sim"
NAO_BUTTON = "Não"

IDEA_MENU_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton(SIM_BUTTON, callback_data=SIM_BUTTON)],
    [InlineKeyboardButton(NAO_BUTTON, callback_data=NAO_BUTTON)]
])

# modelo a ser usado e custo por 1 milhão de tokens input e output
models_ai = [
            ["openai","gpt-3.5-turbo", 0.50, 1,50,OPENAI_API_KEY ], 
            ["togetherai","NousResearch/Nous-Hermes-Llama2-13b", 0.30, 0.30, TOGETHER_API_KEY]
            ]
selected_model = 0
model_ai = models_ai[selected_model]

client = OpenAI()

# Database setup
DB_FILE = "cerebro.db"

def create_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS brainstorming
                      (date TEXT, idea TEXT, resumo TEXT,answer TEXT)''')
    conn.commit()
    conn.close()

def insert_brainstorming(idea,resumo,answer):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO brainstorming (date, idea, resumo, answer) VALUES (?, ?, ?, ?)",
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), idea, resumo, answer))
    conn.commit()
    conn.close()

def handle_message(update: Update, context: CallbackContext) -> None:
    global activate_visualiza
    # print(update.message)
    if update.message.from_user.id not in MY_CHAT_ID:
        text = "Você não está autorizado a usar esse bot."
        context.bot.send_message(update.message.chat.id,text=text)
        print("ID do usuario nao autorizado: " + str(update.message.from_user.id))
        print("Username do usuario nao autorizado: " + str(update.message.from_user.username))
        
    else:

        if update.message.voice is not None or update.message.audio is not None:
            download_file_func(update.message, context.bot.token)
            context.bot.send_message(update.message.chat.id,"Mensagem de audio recebida!")

            print("Transcribing audio file...")

            audio_file= open("download.ogg", "rb")

            result = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
            )

            print(result)

            resultado = parse_message(result.text)

            print(resultado)

            if (resultado[0].lower()) == "ideia":
                text = "Ideia identificada!"
                context.bot.send_message(update.message.chat.id,text=text)
                text = resultado[1]
                context.bot.send_message(update.message.chat.id,text=text)
                idea_menu(update, context)
        
        if update.message.text and activate_visualiza:
            numero_ideia = update.message.text
            print("Ideia: " + numero_ideia)
            activate_visualiza = False

        if update.message.text and not activate_visualiza:
            text = "Olá, eu sou o Cérebro. Como posso te ajudar!"
            context.bot.send_message(update.message.chat.id,text=text)
    

def brainstorm(update, context, ideia):
    print(ideia)
    chat_id = update.callback_query.message.chat_id 
    
    prompt = prompts.prompt_brainstorm
    prompt = prompt + ideia
    
    response = client.chat.completions.create(
        model=model_ai[1],
        messages=[ {"role": "system", "content": prompt},] 
    )

    custo = response.usage.completion_tokens * model_ai[3] / 1E6 + response.usage.prompt_tokens * model_ai[2] / 1E6
    custo = "{:.10f}".format(custo)
    print("Custo: " + (custo))	
    resultado = response.choices[0].message.content
    context.bot.send_message(chat_id=chat_id, text=resultado)
    return resultado


def parse_message(message):
    global ideia, resumo
    prompt =  prompts.prompt_classificador
    prompt = prompt + message
    response = client.chat.completions.create(
        model=model_ai[1],
        messages=[ {"role": "system", "content": prompt},] 
    )
    response_array = eval(response.choices[0].message.content)
    print(response_array[0])
    ideia = response_array[1]
    resumo = response_array[2]
    custo = response.usage.completion_tokens * model_ai[3] / 1E6 + response.usage.prompt_tokens * model_ai[2] / 1E6
    # format to decimal
    custo = "{:.10f}".format(custo)
    print("Custo: " + (custo))	

    return response_array

def start(update: Update, context: CallbackContext) -> None:
    if update.callback_query:
        chat_id = update.callback_query.message.chat_id
    else:
        chat_id = update.message.chat_id
    
    texto = """<b>Seja bem vindo ao Cerebro!</b>
---------------------------------
Comandos:
/lista - lista as ideias salvas
/visualizar - mostra o brainstorm
---------------------------------
    """
    context.bot.send_message(chat_id=chat_id, text=texto, parse_mode=ParseMode.HTML)


def lista(update: Update, context: CallbackContext) -> None:
    # retrieve all rows from the table sqlite brainstorm
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM brainstorming")
    rows = cursor.fetchall()

    if len(rows) > 0:
        context.bot.send_message(update.message.chat_id, 'Ideias salvas:')
        for i, row in enumerate(rows):
            context.bot.send_message(update.message.chat_id, str(i) + "-" + str(row[2]))
    else:
        context.bot.send_message(update.message.chat_id, 'Nenhuma ideia salva!')

def visualizar(update: Update, context: CallbackContext) -> None:
    global activate_visualiza
    context.bot.send_message(update.message.chat_id, 'Qual o numero da ideia que deseja visualizar?')
    activate_visualiza = True
   
def idea_menu(update: Update, context: CallbackContext) -> None: 
    context.bot.send_message(
        update.message.from_user.id,
        IDEA_MENU,
        parse_mode=ParseMode.HTML,
        reply_markup=IDEA_MENU_MARKUP
    )

def button_tap(update: Update, context: CallbackContext) -> None:
    global ideia, resumo
    data = update.callback_query.data
    text = ''
    markup = None

    if data == SIM_BUTTON:
        start_brainstorm = True
    elif data == NAO_BUTTON:
        pass
        
    update.callback_query.message.edit_text("Concluido!")

    update.callback_query.answer()
    
    if start_brainstorm:
        update.callback_query.message.edit_text("Processando...")
        resultado = brainstorm(update, context, ideia)

        insert_brainstorming(ideia,resumo, resultado)

        start_brainstorm = False

    if text:
        update.callback_query.message.edit_text(
        text,
        ParseMode.HTML,
        reply_markup=markup
        )

def main() -> None:
    create_db()

    updater = Updater(TELEGRAM_API_KEY)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("lista", lista))
    dispatcher.add_handler(CommandHandler("visualizar", visualizar))
    dispatcher.add_handler(CallbackQueryHandler(button_tap))
    dispatcher.add_handler(MessageHandler(~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()