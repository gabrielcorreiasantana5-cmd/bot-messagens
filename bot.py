import discord
from discord.ext import commands
import json
import os

TOKEN = "COLOQUE_SEU_TOKEN_AQUI"

ARQUIVO = "usuarios.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# -------------------------
# CARREGAR LISTA
# -------------------------

def carregar_usuarios():
    if not os.path.exists(ARQUIVO):
        return []

    with open(ARQUIVO, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def salvar_usuarios(usuarios):
    with open(ARQUIVO, "w", encoding="utf-8") as arquivo:
        json.dump(usuarios, arquivo, indent=4)


# -------------------------
# BOT ONLINE
# -------------------------

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")


# -------------------------
# ADICIONAR
# -------------------------

@bot.command()
@commands.has_permissions(administrator=True)
async def add(ctx, membro: discord.Member):

    usuarios = carregar_usuarios()

    if membro.id in usuarios:
        await ctx.send("⚠️ Essa pessoa já está na lista.")
        return

    usuarios.append(membro.id)
    salvar_usuarios(usuarios)

    await ctx.send(f"✅ {membro.mention} foi adicionado à lista.")


# -------------------------
# REMOVER
# -------------------------

@bot.command()
@commands.has_permissions(administrator=True)
async def remove(ctx, membro: discord.Member):

    usuarios = carregar_usuarios()

    if membro.id not in usuarios:
        await ctx.send("⚠️ Essa pessoa não está na lista.")
        return

    usuarios.remove(membro.id)
    salvar_usuarios(usuarios)

    await ctx.send(f"✅ {membro.mention} foi removido da lista.")


# -------------------------
# LISTAR
# -------------------------

@bot.command()
@commands.has_permissions(administrator=True)
async def lista(ctx):

    usuarios = carregar_usuarios()

    if not usuarios:
        await ctx.send("📋 A lista está vazia.")
        return

    texto = "📋 **Pessoas cadastradas:**\n\n"

    for numero, user_id in enumerate(usuarios, start=1):

        try:
            usuario = await bot.fetch_user(user_id)
            texto += f"{numero}. {usuario.name}\n"

        except:
            texto += f"{numero}. ID: {user_id}\n"

    await ctx.send(texto)


# -------------------------
# ENVIAR MENSAGEM
# -------------------------

@bot.command()
@commands.has_permissions(administrator=True)
async def avisar(ctx, *, mensagem):

    usuarios = carregar_usuarios()

    if not usuarios:
        await ctx.send("⚠️ Não há ninguém na lista.")
        return

    await ctx.send(
        f"📨 Vou enviar a mensagem para **{len(usuarios)} pessoas**..."
    )

    enviados = 0
    falharam = 0

    for user_id in usuarios:

        try:
            usuario = await bot.fetch_user(user_id)

            await usuario.send(mensagem)

            enviados += 1

        except Exception as erro:

            print(f"Erro com {user_id}: {erro}")
            falharam += 1

    await ctx.send(
        f"✅ Enviadas: **{enviados}**\n"
        f"❌ Falharam: **{falharam}**"
    )


# -------------------------
# TRATAMENTO DE ERROS
# -------------------------

@bot.event
async def on_command_error(ctx, erro):

    if isinstance(erro, commands.MissingPermissions):
        await ctx.send("❌ Você precisa ser administrador.")

    elif isinstance(erro, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Faltou alguma informação no comando.")

    elif isinstance(erro, commands.MemberNotFound):
        await ctx.send("❌ Não encontrei esse usuário no servidor.")


# -------------------------
# INICIAR
# -------------------------

bot.run(TOKEN)
