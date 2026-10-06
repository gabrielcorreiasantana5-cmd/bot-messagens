import discord
from discord.ext import commands
import json
import os


# ==================================================
# CONFIGURAÇÕES
# ==================================================

TOKEN = os.getenv("DISCORD_TOKEN")
ARQUIVO = "usuarios.json"

CARGO_AUTORIZADO = "Corvo Ajudante"


# ==================================================
# INTENTS
# ==================================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ==================================================
# CARREGAR / SALVAR LISTA
# ==================================================

def carregar_usuarios():

    if not os.path.exists(ARQUIVO):
        return []

    try:

        with open(
            ARQUIVO,
            "r",
            encoding="utf-8"
        ) as arquivo:

            return json.load(arquivo)

    except (json.JSONDecodeError, OSError):

        return []


def salvar_usuarios(usuarios):

    with open(
        ARQUIVO,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            usuarios,
            arquivo,
            indent=4
        )


# ==================================================
# PERMISSÕES
# ADM OU CORVO AJUDANTE
# ==================================================

def pode_usar(ctx):

    if ctx.author.guild_permissions.administrator:
        return True

    return any(
        cargo.name == CARGO_AUTORIZADO
        for cargo in ctx.author.roles
    )


# ==================================================
# PROCURAR MEMBRO
# ACEITA:
# @MENÇÃO
# NOME
# NOME DE EXIBIÇÃO
# ID
# ==================================================

async def procurar_membro(ctx, busca):

    busca = busca.strip()

    if not busca:
        return None

    # ----------------------------------------------
    # TENTAR POR MENÇÃO
    # ----------------------------------------------

    if busca.startswith("<@") and busca.endswith(">"):

        id_texto = (
            busca
            .replace("<@", "")
            .replace("!", "")
            .replace(">", "")
        )

        if id_texto.isdigit():

            membro = ctx.guild.get_member(
                int(id_texto)
            )

            if membro:
                return membro

            try:

                membro = await ctx.guild.fetch_member(
                    int(id_texto)
                )

                return membro

            except Exception:
                pass

    # ----------------------------------------------
    # TENTAR POR ID
    # ----------------------------------------------

    if busca.isdigit():

        user_id = int(busca)

        membro = ctx.guild.get_member(
            user_id
        )

        if membro:
            return membro

        try:

            membro = await ctx.guild.fetch_member(
                user_id
            )

            return membro

        except Exception:

            return None

    # ----------------------------------------------
    # TENTAR POR NOME EXATO
    # ----------------------------------------------

    busca_lower = busca.lower()

    encontrados = []

    for membro in ctx.guild.members:

        nomes = {
            membro.name.lower(),
            membro.display_name.lower()
        }

        if membro.global_name:

            nomes.add(
                membro.global_name.lower()
            )

        if busca_lower in nomes:

            encontrados.append(membro)

    # Encontrou exatamente uma pessoa
    if len(encontrados) == 1:

        return encontrados[0]

    # Mais de uma pessoa com o mesmo nome
    if len(encontrados) > 1:

        await ctx.send(
            "⚠️ Encontrei mais de uma pessoa "
            f"com o nome **{busca}**.\n"
            "Use o ID da pessoa para evitar "
            "mandar para a pessoa errada."
        )

        return None

    return None


# ==================================================
# BOT ONLINE
# ==================================================

@bot.event
async def on_ready():

    print(
        f"Bot conectado como {bot.user}"
    )


# ==================================================
# !ADD
#
# EXEMPLOS:
#
# !add @Onix
# !add Onix
# !add 123456789012345678
# ==================================================

@bot.command()
@commands.check(pode_usar)
async def add(ctx, *, pessoa):

    membro = await procurar_membro(
        ctx,
        pessoa
    )

    if not membro:

        await ctx.send(
            "❌ Não encontrei essa pessoa.\n"
            "Tente usar o nome exato, "
            "@menção ou ID."
        )

        return

    usuarios = carregar_usuarios()

    if membro.id in usuarios:

        await ctx.send(
            f"⚠️ {membro.mention} "
            "já está na lista."
        )

        return

    usuarios.append(
        membro.id
    )

    salvar_usuarios(
        usuarios
    )

    await ctx.send(
        f"✅ {membro.mention} "
        "foi adicionado à lista."
    )


# ==================================================
# !REMOVE
#
# EXEMPLOS:
#
# !remove @Onix
# !remove Onix
# !remove 123456789012345678
# ==================================================

@bot.command()
@commands.check(pode_usar)
async def remove(ctx, *, pessoa):

    membro = await procurar_membro(
        ctx,
        pessoa
    )

    if not membro:

        await ctx.send(
            "❌ Não encontrei essa pessoa.\n"
            "Tente usar o nome exato, "
            "@menção ou ID."
        )

        return

    usuarios = carregar_usuarios()

    if membro.id not in usuarios:

        await ctx.send(
            f"⚠️ {membro.mention} "
            "não está na lista."
        )

        return

    usuarios.remove(
        membro.id
    )

    salvar_usuarios(
        usuarios
    )

    await ctx.send(
        f"✅ {membro.mention} "
        "foi removido da lista."
    )


# ==================================================
# !LISTA
# ==================================================

@bot.command()
@commands.check(pode_usar)
async def lista(ctx):

    usuarios = carregar_usuarios()

    if not usuarios:

        await ctx.send(
            "📋 A lista está vazia."
        )

        return

    texto = (
        "📋 **Pessoas cadastradas:**\n\n"
    )

    for numero, user_id in enumerate(
        usuarios,
        start=1
    ):

        try:

            usuario = await bot.fetch_user(
                user_id
            )

            texto += (
                f"{numero}. "
                f"{usuario.name}\n"
            )

        except Exception:

            texto += (
                f"{numero}. "
                f"ID: {user_id}\n"
            )

    await ctx.send(
        texto
    )


# ==================================================
# !AVISAR
#
# ENVIA PARA TODA A LISTA FIXA
#
# EXEMPLO:
#
# !avisar Reunião hoje às 20h.
# ==================================================

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

            usuario = await bot.fetch_user(
                user_id
            )

            await usuario.send(
                mensagem
            )

            enviados += 1

        except Exception as erro:

            print(
                f"Erro ao enviar para "
                f"{user_id}: {erro}"
            )

            falharam += 1

    await ctx.send(
        f"✅ Enviadas: **{enviados}**\n"
        f"❌ Falharam: **{falharam}**"
    )


# ==================================================
# !AVISARCARGO
#
# ENVIA PARA TODO MUNDO DE UM CARGO
#
# EXEMPLO:
#
# !avisarcargo @Academy Mensagem aqui
# ==================================================

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
            "⚠️ Não encontrei ninguém "
            "com esse cargo."
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

            await membro.send(
                mensagem
            )

            enviados += 1

        except Exception as erro:

            print(
                f"Erro ao enviar para "
                f"{membro}: {erro}"
            )

            falharam += 1

    await ctx.send(
        f"✅ Enviadas: **{enviados}**\n"
        f"❌ Falharam: **{falharam}**"
    )


# ==================================================
# !ENVIAR
#
# ENVIO TEMPORÁRIO
# NÃO ALTERA A LISTA
#
# SEPARE AS PESSOAS COM VÍRGULA
#
# EXEMPLOS:
#
# !enviar Onix | Olá
#
# !enviar Onix, shiza, PIRULITO | Olá
#
# !enviar 123456789012345678 | Olá
#
# Pode misturar:
#
# !enviar Onix, 123456789012345678, @Pessoa | Olá
# ==================================================

@bot.command()
@commands.check(pode_usar)
async def enviar(ctx, *, conteudo):

    if "|" not in conteudo:

        await ctx.send(
            "⚠️ Use assim:\n"
            "`!enviar Nome1, Nome2 | Mensagem`"
        )

        return

    parte_pessoas, mensagem = (
        conteudo.split("|", 1)
    )

    mensagem = mensagem.strip()

    if not mensagem:

        await ctx.send(
            "⚠️ Você precisa escrever "
            "uma mensagem."
        )

        return

    buscas = [
        item.strip()
        for item in parte_pessoas.split(",")
        if item.strip()
    ]

    if not buscas:

        await ctx.send(
            "⚠️ Informe pelo menos "
            "uma pessoa."
        )

        return

    membros = []
    ids_adicionados = set()
    nao_encontrados = []

    for busca in buscas:

        membro = await procurar_membro(
            ctx,
            busca
        )

        if not membro:

            nao_encontrados.append(
                busca
            )

            continue

        if membro.bot:
            continue

        if membro.id not in ids_adicionados:

            membros.append(
                membro
            )

            ids_adicionados.add(
                membro.id
            )

    if not membros:

        await ctx.send(
            "❌ Não encontrei nenhum "
            "destinatário válido."
        )

        return

    await ctx.send(
        f"📨 Vou enviar a mensagem para "
        f"**{len(membros)} pessoas**..."
    )

    enviados = 0
    falharam = 0

    for membro in membros:

        try:

            await membro.send(
                mensagem
            )

            enviados += 1

        except Exception as erro:

            print(
                f"Erro ao enviar para "
                f"{membro}: {erro}"
            )

            falharam += 1

    resposta = (
        f"✅ Enviadas: **{enviados}**\n"
        f"❌ Falharam: **{falharam}**"
    )

    if nao_encontrados:

        resposta += (
            "\n⚠️ Não encontrados: "
            + ", ".join(nao_encontrados)
        )

    await ctx.send(
        resposta
    )


# ==================================================
# TRATAMENTO DE ERROS
# ==================================================

@bot.event
async def on_command_error(ctx, erro):

    if isinstance(
        erro,
        commands.CheckFailure
    ):

        await ctx.send(
            "❌ Você precisa ser administrador "
            "ou ter o cargo Corvo Ajudante."
        )

    elif isinstance(
        erro,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            "⚠️ Faltou alguma informação "
            "no comando."
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

        print(
            f"Erro no comando: {erro}"
        )


# ==================================================
# INICIAR BOT
# ==================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN não foi configurado."
    )

bot.run(TOKEN)
