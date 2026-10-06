import discord
from discord.ext import commands
import json
import os


# =========================
# CONFIGURAÇÕES
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")
ARQUIVO = "usuarios.json"


# =========================
# INTENTS
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================
# CARREGAR / SALVAR LISTA
# =========================

def carregar_usuarios():
    if not os.path.exists(ARQUIVO):
        return []

    try:
        with open(ARQUIVO, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, OSError):
        return []


def salvar_usuarios(usuarios):
    with open(ARQUIVO, "w", encoding="utf-8") as arquivo:
        json.dump(usuarios, arquivo, indent=4)


# =========================
# PERMISSÕES
# ADM OU CORVO AJUDANTE
# =========================

def pode_usar(ctx):
    if ctx.author.guild_permissions.administrator:
        return True

    return any(
        role.name == "Corvo Ajudante"
        for role in ctx.author.roles
    )


# =========================
# BOT ONLINE
# =========================

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")


# =========================
# !ADD
# ADICIONAR À LISTA FIXA
# =========================

@bot.command()
@commands.check(pode_usar)
async def add(ctx, membro: discord.Member):

    usuarios = carregar_usuarios()

    if membro.id in usuarios:
        await ctx.send(
            "⚠️ Essa pessoa já está na lista."
        )
        return

    usuarios.append(membro.id)
    salvar_usuarios(usuarios)

    await ctx.send(
        f"✅ {membro.mention} foi adicionado à lista."
    )


# =========================
# !REMOVE
# REMOVER DA LISTA FIXA
# =========================

@bot.command()
@commands.check(pode_usar)
async def remove(ctx, membro: discord.Member):

    usuarios = carregar_usuarios()

    if membro.id not in usuarios:
        await ctx.send(
            "⚠️ Essa pessoa não está na lista."
        )
        return

    usuarios.remove(membro.id)
    salvar_usuarios(usuarios)

    await ctx.send(
        f"✅ {membro.mention} foi removido da lista."
    )


# =========================
# !LISTA
# MOSTRAR LISTA FIXA
# =========================

@bot.command()
@commands.check(pode_usar)
async def lista(ctx):

    usuarios = carregar_usuarios()

    if not usuarios:
        await ctx.send(
            "📋 A lista está vazia."
        )
        return

    texto = "📋 **Pessoas cadastradas:**\n\n"

    for numero, user_id in enumerate(
        usuarios,
        start=1
    ):

        try:
            usuario = await bot.fetch_user(user_id)
            texto += f"{numero}. {usuario.name}\n"

        except Exception:
            texto += f"{numero}. ID: {user_id}\n"

    await ctx.send(texto)


# =========================
# !AVISAR
# MANDAR PARA A LISTA FIXA
# =========================

@bot.command()
@commands.check(pode_usar)
async def avisar(ctx, *, mensagem):

    usuarios = carregar_usuarios()

    if not usuarios:
        await ctx.send(
            "⚠️ Não há ninguém na lista."
        )
        return

    await ctx.send(
        f"📨 Vou enviar a mensagem para "
        f"**{len(usuarios)} pessoas**..."
    )

    enviados = 0
    falharam = 0

    for user_id in usuarios:

        try:
            usuario = await bot.fetch_user(user_id)
            await usuario.send(mensagem)
            enviados += 1

        except Exception as erro:
            print(
                f"Erro ao enviar para {user_id}: {erro}"
            )
            falharam += 1

    await ctx.send(
        f"✅ Enviadas: **{enviados}**\n"
        f"❌ Falharam: **{falharam}**"
    )


# =========================
# !AVISARCARGO
# MANDAR PARA UM CARGO INTEIRO
# =========================

@bot.command()
@commands.check(pode_usar)
async def avisarcargo(
    ctx,
    cargo: discord.Role,
    *,
    mensagem
):

    membros = [
        membro
        for membro in cargo.members
        if not membro.bot
    ]

    if not membros:
        await ctx.send(
            "⚠️ Não encontrei membros com esse cargo."
        )
        return

    await ctx.send(
        f"📨 Vou enviar para "
        f"**{len(membros)} pessoas** "
        f"do cargo **{cargo.name}**..."
    )

    enviados = 0
    falharam = 0

    for membro in membros:

        try:
            await membro.send(mensagem)
            enviados += 1

        except Exception as erro:
            print(
                f"Erro ao enviar para {membro}: {erro}"
            )
            falharam += 1

    await ctx.send(
        f"✅ Enviadas: **{enviados}**\n"
        f"❌ Falharam: **{falharam}**"
    )


# =========================
# !ENVIAR
# MANDAR PARA PESSOAS ESPECÍFICAS
# SEM ALTERAR A LISTA
# =========================

@bot.command()
@commands.check(pode_usar)
async def enviar(ctx, *, conteudo):

    if "|" not in conteudo:
        await ctx.send(
            "⚠️ Use assim:\n"
            "!enviar @Pessoa1 @Pessoa2 | Sua mensagem"
        )
        return

    _, mensagem = conteudo.split("|", 1)
    mensagem = mensagem.strip()

    if not mensagem:
        await ctx.send(
            "⚠️ Você precisa escrever uma mensagem."
        )
        return

    membros = ctx.message.mentions

    if not membros:
        await ctx.send(
            "⚠️ Você precisa mencionar pelo menos uma pessoa."
        )
        return

    membros_unicos = []
    ids_adicionados = set()

    for membro in membros:

        if membro.bot:
            continue

        if membro.id not in ids_adicionados:
            membros_unicos.append(membro)
            ids_adicionados.add(membro.id)

    if not membros_unicos:
        await ctx.send(
            "⚠️ Não encontrei nenhum usuário válido."
        )
        return

    await ctx.send(
        f"📨 Vou enviar a mensagem para "
        f"**{len(membros_unicos)} pessoas**..."
    )

    enviados = 0
    falharam = 0

    for membro in membros_unicos:

        try:
            await membro.send(mensagem)
            enviados += 1

        except Exception as erro:
            print(
                f"Erro ao enviar para {membro}: {erro}"
            )
            falharam += 1

    await ctx.send(
        f"✅ Enviadas: **{enviados}**\n"
        f"❌ Falharam: **{falharam}**"
    )


# =========================
# TRATAMENTO DE ERROS
# =========================

@bot.event
async def on_command_error(ctx, erro):

    if isinstance(erro, commands.CheckFailure):

        await ctx.send(
            "❌ Você precisa ser administrador "
            "ou ter o cargo Corvo Ajudante."
        )

    elif isinstance(
        erro,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            "⚠️ Faltou alguma informação no comando."
        )

    elif isinstance(
        erro,
        commands.MemberNotFound
    ):

        await ctx.send(
            "❌ Não encontrei esse usuário no servidor."
        )

    elif isinstance(
        erro,
        commands.RoleNotFound
    ):

        await ctx.send(
            "❌ Não encontrei esse cargo."
        )

    elif isinstance(
        erro,
        commands.CommandNotFound
    ):

        return

    else:
        print(f"Erro no comando: {erro}")


# =========================
# INICIAR BOT
# =========================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN não foi configurado."
    )

bot.run(TOKEN)
