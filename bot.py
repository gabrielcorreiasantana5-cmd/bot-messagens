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
    if ctx.author.guild_permissions.administrator:
        return True
    return any(cargo.name == CARGO_AUTORIZADO for cargo in ctx.author.roles)


def canal_temporario(ctx):
    return ctx.guild is not None and ctx.channel.name == CANAL_COMANDOS


async def apagar_depois(mensagem):
    await asyncio.sleep(TEMPO_APAGAR)
    try:
        await mensagem.delete()
    except (discord.Forbidden, discord.NotFound, discord.HTTPException) as erro:
        print(f'N茫o foi poss铆vel apagar mensagem: {erro}')


async def responder(ctx, texto):
    resposta = await ctx.send(texto)
    if canal_temporario(ctx):
        asyncio.create_task(apagar_depois(resposta))
    return resposta


@bot.before_invoke
async def apagar_comando(ctx):
    if canal_temporario(ctx):
        asyncio.create_task(apagar_depois(ctx.message))


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
        await responder(ctx, f'鈿狅笍 Encontrei mais de uma pessoa com o nome **{busca}**.\nUse o ID da pessoa para evitar mandar para a pessoa errada.')
    return None


async def registrar_log(ctx, comando, mensagem, destinatarios, enviados, falharam, detalhes=''):
    canal = discord.utils.get(ctx.guild.text_channels, name=CANAL_LOGS)
    if canal is None:
        print(f'ERRO LOGS: canal #{CANAL_LOGS} n茫o encontrado no servidor {ctx.guild.name}')
        return
    momento = datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')
    cabecalho = (
        f'馃搵 **Registro de envio 鈥� !{comando}**\n'
        f'馃懁 Respons谩vel: {ctx.author} (ID: {ctx.author.id})\n'
        f'馃晵 Data: {momento}\n'
        f'馃摠 Destinat谩rios: {destinatarios}\n'
        f'鉁� Enviadas: {enviados} | 鉂� Falharam: {falharam}\n'
    )
    if detalhes:
        cabecalho += f'鈩癸笍 {detalhes}\n'
    cabecalho += '馃摑 **Mensagem enviada:**\n'
    # Divide textos longos para respeitar o limite de 2.000 caracteres do Discord.
    try:
        await canal.send(cabecalho, allowed_mentions=discord.AllowedMentions.none())
        texto = mensagem or '(vazia)'
        for inicio in range(0, len(texto), 1900):
            await canal.send(texto[inicio:inicio + 1900], allowed_mentions=discord.AllowedMentions.none())
    except (discord.Forbidden, discord.HTTPException) as erro:
        print(f'ERRO AO ENVIAR LOG para #{CANAL_LOGS}: {erro}')


@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')


@bot.command()
@commands.check(pode_usar)
async def add(ctx, *, pessoa):
    membro = await procurar_membro(ctx, pessoa)
    if not membro:
        await responder(ctx, '鉂� N茫o encontrei essa pessoa.\nTente usar o nome exato, @men莽茫o ou ID.')
        return
    usuarios = carregar_usuarios()
    if membro.id in usuarios:
        await responder(ctx, f'鈿狅笍 {membro.mention} j谩 est谩 na lista.')
        return
    usuarios.append(membro.id)
    salvar_usuarios(usuarios)
    await responder(ctx, f'鉁� {membro.mention} foi adicionado 脿 lista.')


@bot.command()
@commands.check(pode_usar)
async def remove(ctx, *, pessoa):
    membro = await procurar_membro(ctx, pessoa)
    if not membro:
        await responder(ctx, '鉂� N茫o encontrei essa pessoa.\nTente usar o nome exato, @men莽茫o ou ID.')
        return
    usuarios = carregar_usuarios()
    if membro.id not in usuarios:
        await responder(ctx, f'鈿狅笍 {membro.mention} n茫o est谩 na lista.')
        return
    usuarios.remove(membro.id)
    salvar_usuarios(usuarios)
    await responder(ctx, f'鉁� {membro.mention} foi removido da lista.')


@bot.command()
@commands.check(pode_usar)
async def lista(ctx):
    usuarios = carregar_usuarios()
    if not usuarios:
        await responder(ctx, '馃搵 A lista est谩 vazia.')
        return
    texto = '馃搵 **Pessoas cadastradas:**\n\n'
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
        await responder(ctx, '鈿狅笍 N茫o h谩 ningu茅m na lista.')
        return
    await responder(ctx, f'馃摠 Vou enviar a mensagem para **{len(usuarios)} pessoas**...')
    enviados = falharam = 0
    for user_id in usuarios:
        try:
            usuario = await bot.fetch_user(user_id)
            await usuario.send(mensagem)
            enviados += 1
        except Exception as erro:
            print(f'Erro ao enviar para {user_id}: {erro}')
            falharam += 1
    await responder(ctx, f'鉁� Enviadas: **{enviados}**\n鉂� Falharam: **{falharam}**')
    await registrar_log(ctx, 'avisar', mensagem, f'{len(usuarios)} pessoas da lista (IDs: {", ".join(map(str, usuarios))})', enviados, falharam)


@bot.command()
@commands.check(pode_usar)
async def avisarcargo(ctx, cargo: discord.Role, *, mensagem):
    membros = [membro for membro in cargo.members if not membro.bot]
    if not membros:
        await responder(ctx, '鈿狅笍 N茫o encontrei ningu茅m com esse cargo.')
        return
    await responder(ctx, f'馃摠 Vou enviar para **{len(membros)} pessoas** do cargo **{cargo.name}**...')
    enviados = falharam = 0
    for membro in membros:
        try:
            await membro.send(mensagem)
            enviados += 1
        except Exception as erro:
            print(f'Erro ao enviar para {membro}: {erro}')
            falharam += 1
    await responder(ctx, f'鉁� Enviadas: **{enviados}**\n鉂� Falharam: **{falharam}**')
    await registrar_log(ctx, 'avisarcargo', mensagem, f'{len(membros)} membros do cargo {cargo.name} (ID: {cargo.id})', enviados, falharam)


@bot.command()
@commands.check(pode_usar)
async def enviar(ctx, *, conteudo):
    if '|' not in conteudo:
        await responder(ctx, '鈿狅笍 Use assim:\n`!enviar Nome1, Nome2 | Mensagem`')
        return
    parte_pessoas, mensagem = conteudo.split('|', 1)
    mensagem = mensagem.strip()
    if not mensagem:
        await responder(ctx, '鈿狅笍 Voc锚 precisa escrever uma mensagem.')
        return
    buscas = [item.strip() for item in parte_pessoas.split(',') if item.strip()]
    if not buscas:
        await responder(ctx, '鈿狅笍 Informe pelo menos uma pessoa.')
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
        await responder(ctx, '鉂� N茫o encontrei nenhum destinat谩rio v谩lido.')
        return
    await responder(ctx, f'馃摠 Vou enviar a mensagem para **{len(membros)} pessoas**...')
    enviados = falharam = 0
    for membro in membros:
        try:
            await membro.send(mensagem)
            enviados += 1
        except Exception as erro:
            print(f'Erro ao enviar para {membro}: {erro}')
            falharam += 1
    resposta = f'鉁� Enviadas: **{enviados}**\n鉂� Falharam: **{falharam}**'
    if nao_encontrados:
        resposta += '\n鈿狅笍 N茫o encontrados: ' + ', '.join(nao_encontrados)
    await responder(ctx, resposta)
    destinos = ', '.join(f'{membro} (ID: {membro.id})' for membro in membros)
    await registrar_log(ctx, 'enviar', mensagem, destinos, enviados, falharam,
                       'N茫o encontrados: ' + ', '.join(nao_encontrados) if nao_encontrados else '')


@bot.event
async def on_command_error(ctx, erro):
    # before_invoke n茫o executa quando o comando falha na checagem ou no parsing.
    if canal_temporario(ctx):
        asyncio.create_task(apagar_depois(ctx.message))
    if isinstance(erro, commands.CheckFailure):
        await responder(ctx, '鉂� Voc锚 precisa ser administrador ou ter o cargo Corvo Ajudante.')
    elif isinstance(erro, commands.MissingRequiredArgument):
        await responder(ctx, '鈿狅笍 Faltou alguma informa莽茫o no comando.')
    elif isinstance(erro, commands.RoleNotFound):
        await responder(ctx, '鉂� N茫o encontrei esse cargo.')
    elif isinstance(erro, commands.CommandNotFound):
        return
    else:
        print(f'Erro no comando: {erro}')


if not TOKEN:
    raise RuntimeError('DISCORD_TOKEN n茫o foi configurado.')
bot.run(TOKEN)
