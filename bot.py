import asyncio
import json
import os
from datetime import datetime, timezone

import discord
from discord.ext import commands

TOKEN = os.getenv('DISCORD_TOKEN')
ARQUIVO = 'usuarios.json'
CARGO_AUTORIZADO = 'Corvo Ajudante'
CANAL_COMANDOS = 'bot-academy'
CANAL_LOGS = 'logs-covil'
TEMPO_APAGAR = 5

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)


def carregar_usuarios():
    if not os.path.exists(ARQUIVO):
        return []
    try:
        with open(ARQUIVO, 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, OSError):
        return []


def salvar_usuarios(usuarios):
    with open(ARQUIVO, 'w', encoding='utf-8') as arquivo:
        json.dump(usuarios, arquivo, indent=4)


def pode_usar(ctx):
    if ctx.guild is None:
        return False
    if ctx.author.guild_permissions.administrator:
        return True
    return any(cargo.name == CARGO_AUTORIZADO for cargo in ctx.author.roles)


def canal_temporario(ctx):
    return ctx.guild is not None and ctx.channel.name == CANAL_COMANDOS


async def apagar_depois(mensagem):
    await asyncio.sleep(TEMPO_APAGAR)
    try:
        await mensagem.delete()
    except discord.NotFound:
        pass  # A mensagem j\u00e1 foi apagada.
    except discord.Forbidden:
        print(f'ERRO AO APAGAR: sem permiss\u00e3o no canal #{mensagem.channel.name}. '
              'Conceda Gerenciar mensagens ao bot nas permiss\u00f5es deste canal.')
    except discord.HTTPException as erro:
        print(f'ERRO AO APAGAR mensagem {mensagem.id}: {erro}')


async def responder(ctx, texto):
    resposta = await ctx.send(texto)
    if canal_temporario(ctx):
        asyncio.create_task(apagar_depois(resposta))
    return resposta


@bot.event
async def on_message(message):
    # Agenda a exclus\u00e3o assim que o comando chega, inclusive em caso de erro.
    if (message.guild is not None
            and not message.author.bot
            and message.channel.name == CANAL_COMANDOS
            and message.content.startswith('!')):
        asyncio.create_task(apagar_depois(message))
    await bot.process_commands(message)


async def procurar_membro(ctx, busca):
    busca = busca.strip()
    if not busca:
        return None
    if busca.startswith('<@') and busca.endswith('>'):
        id_texto = busca.replace('<@', '').replace('!', '').replace('>', '')
        if id_texto.isdigit():
            membro = ctx.guild.get_member(int(id_texto))
            if membro:
                return membro
            try:
                return await ctx.guild.fetch_member(int(id_texto))
            except discord.HTTPException:
                pass
    if busca.isdigit():
        user_id = int(busca)
        membro = ctx.guild.get_member(user_id)
        if membro:
            return membro
        try:
            return await ctx.guild.fetch_member(user_id)
        except discord.HTTPException:
            return None
    busca_lower = busca.lower()
    encontrados = []
    for membro in ctx.guild.members:
        nomes = {membro.name.lower(), membro.display_name.lower()}
        if membro.global_name:
            nomes.add(membro.global_name.lower())
        if busca_lower in nomes:
            encontrados.append(membro)
    if len(encontrados) == 1:
        return encontrados[0]
    if len(encontrados) > 1:
        await responder(ctx, f'\u26a0\ufe0f Encontrei mais de uma pessoa com o nome **{busca}**.\n'
                            'Use o ID da pessoa para evitar mandar para a pessoa errada.')
    return None


async def registrar_log(ctx, comando, mensagem, destinatarios, enviados, falharam, detalhes=''):
    canal = discord.utils.get(ctx.guild.text_channels, name=CANAL_LOGS)
    if canal is None:
        print(f'ERRO LOGS: canal #{CANAL_LOGS} n\u00e3o encontrado no servidor {ctx.guild.name}')
        return
    momento = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    cabecalho = (
        f'\U0001f4cb **Registro de envio \u2014 !{comando}**\n'
        f'\U0001f464 Respons\u00e1vel: {ctx.author} (ID: {ctx.author.id})\n'
        f'\U0001f552 Data: {momento}\n'
        f'\U0001f4e8 Destinat\u00e1rios: {destinatarios}\n'
        f'\u2705 Enviadas: {enviados} | \u274c Falharam: {falharam}\n'
    )
    if detalhes:
        cabecalho += f'\u2139\ufe0f {detalhes}\n'
    cabecalho += '\U0001f4dd **Mensagem enviada:**\n'
    try:
        # Mant\u00e9m o limite de caracteres mesmo para listas de destinat\u00e1rios grandes.
        for inicio in range(0, len(cabecalho), 1900):
            await canal.send(cabecalho[inicio:inicio + 1900],
                             allowed_mentions=discord.AllowedMentions.none())
        texto = mensagem or '(vazia)'
        for inicio in range(0, len(texto), 1900):
            await canal.send(texto[inicio:inicio + 1900],
                             allowed_mentions=discord.AllowedMentions.none())
    except (discord.Forbidden, discord.HTTPException) as erro:
        print(f'ERRO AO ENVIAR LOG para #{CANAL_LOGS}: {erro}')


@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    print(f'Apagamento ap\u00f3s {TEMPO_APAGAR}s no #{CANAL_COMANDOS}; logs no #{CANAL_LOGS}')


@bot.command()
@commands.check(pode_usar)
async def add(ctx, *, pessoa):
    membro = await procurar_membro(ctx, pessoa)
    if not membro:
        await responder(ctx, '\u274c N\u00e3o encontrei essa pessoa.\nTente usar o nome exato, @men\u00e7\u00e3o ou ID.')
        return
    usuarios = carregar_usuarios()
    if membro.id in usuarios:
        await responder(ctx, f'\u26a0\ufe0f {membro.mention} j\u00e1 est\u00e1 na lista.')
        return
    usuarios.append(membro.id)
    salvar_usuarios(usuarios)
    await responder(ctx, f'\u2705 {membro.mention} foi adicionado \u00e0 lista.')


@bot.command()
@commands.check(pode_usar)
async def remove(ctx, *, pessoa):
    membro = await procurar_membro(ctx, pessoa)
    if not membro:
        await responder(ctx, '\u274c N\u00e3o encontrei essa pessoa.\nTente usar o nome exato, @men\u00e7\u00e3o ou ID.')
        return
    usuarios = carregar_usuarios()
    if membro.id not in usuarios:
        await responder(ctx, f'\u26a0\ufe0f {membro.mention} n\u00e3o est\u00e1 na lista.')
        return
    usuarios.remove(membro.id)
    salvar_usuarios(usuarios)
    await responder(ctx, f'\u2705 {membro.mention} foi removido da lista.')


@bot.command()
@commands.check(pode_usar)
async def lista(ctx):
    usuarios = carregar_usuarios()
    if not usuarios:
        await responder(ctx, '\U0001f4cb A lista est\u00e1 vazia.')
        return
    texto = '\U0001f4cb **Pessoas cadastradas:**\n\n'
    for numero, user_id in enumerate(usuarios, start=1):
        try:
            usuario = await bot.fetch_user(user_id)
            linha = f'{numero}. {usuario.name}\n'
        except Exception:
            linha = f'{numero}. ID: {user_id}\n'
        if len(texto) + len(linha) > 1900:
            await responder(ctx, texto)
            texto = ''
        texto += linha
    if texto:
        await responder(ctx, texto)


@bot.command()
@commands.check(pode_usar)
async def avisar(ctx, *, mensagem):
    usuarios = carregar_usuarios()
    if not usuarios:
        await responder(ctx, '\u26a0\ufe0f N\u00e3o h\u00e1 ningu\u00e9m na lista.')
        return
    await responder(ctx, f'\U0001f4e8 Vou enviar a mensagem para **{len(usuarios)} pessoas**...')
    enviados = falharam = 0
    for user_id in usuarios:
        try:
            usuario = await bot.fetch_user(user_id)
            await usuario.send(mensagem)
            enviados += 1
        except Exception as erro:
            print(f'Erro ao enviar para {user_id}: {erro}')
            falharam += 1
    await responder(ctx, f'\u2705 Enviadas: **{enviados}**\n\u274c Falharam: **{falharam}**')
    await registrar_log(ctx, 'avisar', mensagem,
                        f'{len(usuarios)} pessoas da lista (IDs: {", ".join(map(str, usuarios))})',
                        enviados, falharam)


@bot.command()
@commands.check(pode_usar)
async def avisarcargo(ctx, cargo: discord.Role, *, mensagem):
    membros = [membro for membro in cargo.members if not membro.bot]
    if not membros:
        await responder(ctx, '\u26a0\ufe0f N\u00e3o encontrei ningu\u00e9m com esse cargo.')
        return
    await responder(ctx, f'\U0001f4e8 Vou enviar para **{len(membros)} pessoas** do cargo **{cargo.name}**...')
    enviados = falharam = 0
    for membro in membros:
        try:
            await membro.send(mensagem)
            enviados += 1
        except Exception as erro:
            print(f'Erro ao enviar para {membro}: {erro}')
            falharam += 1
    await responder(ctx, f'\u2705 Enviadas: **{enviados}**\n\u274c Falharam: **{falharam}**')
    await registrar_log(ctx, 'avisarcargo', mensagem,
                        f'{len(membros)} membros do cargo {cargo.name} (ID: {cargo.id})',
                        enviados, falharam)


@bot.command()
@commands.check(pode_usar)
async def enviar(ctx, *, conteudo):
    if '|' not in conteudo:
        await responder(ctx, '\u26a0\ufe0f Use assim:\n`!enviar Nome1, Nome2 | Mensagem`')
        return
    parte_pessoas, mensagem = conteudo.split('|', 1)
    mensagem = mensagem.strip()
    if not mensagem:
        await responder(ctx, '\u26a0\ufe0f Voc\u00ea precisa escrever uma mensagem.')
        return
    buscas = [item.strip() for item in parte_pessoas.split(',') if item.strip()]
    if not buscas:
        await responder(ctx, '\u26a0\ufe0f Informe pelo menos uma pessoa.')
        return
    membros = []
    ids_adicionados = set()
    nao_encontrados = []
    for busca in buscas:
        membro = await procurar_membro(ctx, busca)
        if not membro:
            nao_encontrados.append(busca)
            continue
        if membro.bot:
            continue
        if membro.id not in ids_adicionados:
            membros.append(membro)
            ids_adicionados.add(membro.id)
    if not membros:
        await responder(ctx, '\u274c N\u00e3o encontrei nenhum destinat\u00e1rio v\u00e1lido.')
        return
    await responder(ctx, f'\U0001f4e8 Vou enviar a mensagem para **{len(membros)} pessoas**...')
    enviados = falharam = 0
    for membro in membros:
        try:
            await membro.send(mensagem)
            enviados += 1
        except Exception as erro:
            print(f'Erro ao enviar para {membro}: {erro}')
            falharam += 1
    resposta = f'\u2705 Enviadas: **{enviados}**\n\u274c Falharam: **{falharam}**'
    if nao_encontrados:
        resposta += '\n\u26a0\ufe0f N\u00e3o encontrados: ' + ', '.join(nao_encontrados)
    await responder(ctx, resposta)
    destinos = ', '.join(f'{membro} (ID: {membro.id})' for membro in membros)
    await registrar_log(ctx, 'enviar', mensagem, destinos, enviados, falharam,
                        'N\u00e3o encontrados: ' + ', '.join(nao_encontrados) if nao_encontrados else '')


@bot.event
async def on_command_error(ctx, erro):
    if isinstance(erro, commands.CheckFailure):
        await responder(ctx, '\u274c Voc\u00ea precisa ser administrador ou ter o cargo Corvo Ajudante.')
    elif isinstance(erro, commands.MissingRequiredArgument):
        await responder(ctx, '\u26a0\ufe0f Faltou alguma informa\u00e7\u00e3o no comando.')
    elif isinstance(erro, commands.RoleNotFound):
        await responder(ctx, '\u274c N\u00e3o encontrei esse cargo.')
    elif isinstance(erro, commands.CommandNotFound):
        return
    else:
        print(f'Erro no comando: {erro}')


if not TOKEN:
    raise RuntimeError('DISCORD_TOKEN n\u00e3o foi configurado.')
bot.run(TOKEN)
