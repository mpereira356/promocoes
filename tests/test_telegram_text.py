import asyncio
from unittest.mock import AsyncMock
from monitor.telegram_text import render, parts, send_text


def test_dynamic_titles_are_bold_but_cannot_inject_html():
    title = 'Board <b>fake</b> & DDR4'
    result = render(title + '\nBUSCAS\nPayment < 100', (title,))
    assert result == '<b>Board &lt;b&gt;fake&lt;/b&gt; &amp; DDR4</b>\n<b>BUSCAS</b>\nPayment &lt; 100'


def test_chunks_keep_emoji_intact_and_reconstruct_original():
    text = '🏆 ' * 3000 + '\nBUSCAS\n' + '&<>\n' * 2000
    split = list(parts(text))
    assert ''.join(split) == text
    assert all(len(part.encode('utf-16-le')) // 2 <= 3800 for part in split)


def test_html_is_rendered_after_splitting_and_preserves_keyboard():
    async def scenario():
        send = AsyncMock()
        await send_text(send, 'BUSCAS\n' + '<' * 4000, reply_markup='keyboard')
        assert send.await_count > 1
        assert send.await_args_list[0].args[0] == '<b>BUSCAS</b>\n'
        for call in send.await_args_list:
            assert call.kwargs == {'parse_mode': 'HTML', 'reply_markup': 'keyboard'}
            assert call.args[0].count('<b>') == call.args[0].count('</b>')
    asyncio.run(scenario())
