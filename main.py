from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import AstrBotConfig, Image, Plain
from astrbot.core.utils.t2i.renderer import HtmlRenderer 

from pathlib import Path
from jinja2 import Template
import textwrap
import json
import random
import base64

@register("harrowing", "Garrise", "Pathfinder哈罗牌占卜插件", "0.0.1")
class HarrowingPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.context = context
        self.harrow_json = Path(__file__).parent / "harrow.json"
        resources_path_str: str = config.get("resources_path", "resources")
        self.resources_path: Path = Path(__file__).parent / resources_path_str
    
    def search_card(self, cards, name):
        for card in cards:
            if name == card['name'] or name == card['name-en']:
                return card
        return None

    def get_img(self, card):
        img_path = self.resources_path / f"{card['num']}.jpg"
        return f"data:image/jpg;base64,{base64.b64encode((img_path).read_bytes()).decode()}"

    def make_harrowing(self, choosing: str = ""):
        if choosing == "力量" or choosing == "锤":
            deck = "hammer"
        elif choosing == "敏捷" or choosing == "钥":
            deck = "key"
        elif choosing == "体质" or choosing == "盾":
            deck = "shield"
        elif choosing == "智力" or choosing == "书":
            deck = "book"
        elif choosing == "感知" or choosing == "星":
            deck = "star"
        elif choosing == "魅力" or choosing == "冠":
            deck = "crown"
        else:
            return None
        with open(self.harrow_json, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        cards = data[deck]
        chosen = random.choice(cards)
        dictionary = {}
        dictionary.update({"chosen": chosen})
        dictionary.update({"chosen_img": self.get_img(chosen)})
        decks = ["hammer", "key", "shield", "book", "star", "crown"]
        cards = []
        for deck in decks:
            cards.extend(data[deck])
        spread = random.sample(cards, 9)
        aligns = iter(["00", "01", "02", "10", "11", "12", "20", "21", "22"])
        matches = []
        images = []
        for card in spread:
            align = next(aligns)
            images.append(self.get_img(card))
            match = {}
            if card == chosen:
                match.update({"chosen":1})
            else:
                match.update({"chosen":0})
            if align == card["align"]:
                match.update({"align":1}) #True Match = 1
            elif int(align) + int(card["align"]) == 22 and align != card["align"]:
                match.update({"align":2}) #Opposite Match = 2
            elif align[0:1] == card["align"][0:1] or align[-1:] == card["align"][-1:]:
                match.update({"align":3}) #Partial Match = 3
            else:
                match.update({"align":0}) #No Match = 0
            if int(align[-1:]) + int(card["align"][-1:]) == 2 and align[-1:] != card["align"][-1:]:
                match.update({"misaligned":1})
            else:
                match.update({"misaligned":0})
            matches.append(match)
        dictionary.update({"matches": matches})
        dictionary.update({"spread": spread})
        dictionary.update({"images": images})
        return dictionary
    
    @filter.command_group("哈罗牌", alias={"harrow"})
    def harrow():
        pass
    
    @harrow.command("帮助", alias={"help"})
    async def help_handler(self, event: AstrMessageEvent, text: str = ""):
        yield event.plain_result(textwrap.dedent('''
            Pathfinder哈罗牌占卜插件使用说明：
            1. 占卜指令：
                - 指令：哈罗牌 占卜 [属性或卡组名称]
                - 说明：进行一次牌阵占卜，需填入占卜目的所对应的属性或卡组名。
                - 示例：哈罗牌 占卜 力量
            2. 抽卡指令：
                - 指令：哈罗牌 抽卡
                - 说明：随机抽取一张哈罗牌进行解读。
            3. 查看指令：
                - 指令：哈罗牌 查看 [牌名]
                - 说明：查看指定哈罗牌的详细信息。
            '''))

    @harrow.command("占卜", alias={"divine"})
    async def divine_handler(self, event: AstrMessageEvent, text: str = ""):
        dictionary = self.make_harrowing(text)
        if dictionary:
            path = Path(__file__).parent / "template" / "spread.html"
            with open(str(path), "r", encoding="utf-8") as f:
                tmpl_str = f.read()
            page_option = {"viewport": {"width": 750, "height": 10}, "device_scale_factor": 2.0}
            url = await self.html_render(tmpl_str, dictionary)
            yield event.image_result(url)
        else:
            yield event.chain_result([Plain("找不到指定卡组或属性！")])

    @harrow.command("抽卡", alias={"draw"})
    async def draw_handler(self, event: AstrMessageEvent, text: str = ""):
        with open(self.harrow_json, "r", encoding="utf-8") as f:
            content = json.load(f)
        decks = content.keys()
        cards = []
        for deck in decks:
            cards.extend(content[deck])
        card = random.choice(cards)
        card_filename = "{}.jpg".format(card["num"])
        card_path = self.resources_path / card_filename
        yield event.chain_result([Plain(f"{card['name']}{card['name-en']}\n[{card['deck']}] [{card['attribute']}] [{card['alignment']}]"),Image.fromFileSystem(str(card_path)), Plain(card["meaning"])])

    @harrow.command("查看", alias={"view"})
    async def view_handler(self, event: AstrMessageEvent, text: str = ""):
        with open(self.harrow_json, "r", encoding="utf-8") as f:
            content = json.load(f)
        decks = content.keys()
        cards = []
        for deck in decks:
            cards.extend(content[deck])
        card = self.search_card(cards, text)
        if card:
            card_filename = "{}.jpg".format(card["num"])
            card_path = self.resources_path / card_filename
            yield event.chain_result([Plain(f"{card['name']}{card['name-en']}\n[{card['deck']}] [{card['attribute']}] [{card['alignment']}]"),Image.fromFileSystem(str(card_path)), Plain(card["meaning"])])
        else:
            yield event.chain_result([Plain("找不到指定哈罗牌！")])