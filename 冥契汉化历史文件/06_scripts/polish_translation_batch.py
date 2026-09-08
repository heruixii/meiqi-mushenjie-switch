"""Apply conservative, project-wide cleanup to machine-generated batches."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


REPLACEMENTS = {
    "安布尔": "琥珀",
    "Riyo": "理世",
    "Rize": "理世",
    "里代": "理世",
    "理代": "理世",
    "纽米亚": "匂宫",
    "纽米娅": "匂宫",
    "新宫": "匂宫",
    "尼欧米亚": "匂宫",
    "尼乌米娅": "匂宫",
    "纽米": "匂宫",
    "“": "「",
    "”": "」",
    "‘": "『",
    "’": "』",
    "...": "……",
    "…": "……",
}

SCENE_OVERRIDES = {
    "Script/scenario02_1.binu8@74738": "@vrize_0015「你现在可是被讨厌得很呢。毕竟那个人最讨厌天才了。」",
    "Script/scenario02_1.binu8@74944": "@vrize_0016「那个新来的孩子……真厉害。已经好久没让我背脊发凉了。」",
    "Script/scenario02_1.binu8@75094": "@vrize_0017「简直就像在看折原冰狐的演技。压倒性的、支配性的……」",
    "Script/scenario02_1.binu8@75341": "@vrize_0018「……是吗。」",
    "Script/scenario02_1.binu8@75422": "@vrize_0019「我很期待你作为演出家的未来。所以，加油吧。」",
    "Script/scenario02_1.binu8@75941": "@vNanana_0013「我也想看看哥哥演的戏。」",
    "Script/scenario02_1.binu8@76212": "@vNanana_0014「即便如此，作为妹妹，我还是想看看哥哥登上舞台的样子……」",
    "Script/scenario02_1.binu8@76469": "@vNanana_0015「才没有那回事！那可是哥哥努力创作出来的作品，所以就算再害怕、再恐怖，我也会看到最后！！」",
    "Script/scenario02_1.binu8@76717": "@vNanana_0016「呜、呜呜呜……」",
    "Script/scenario02_1.binu8@76884": "@vNanana_0017「我、我当然会看……！赌上妹妹的尊严！！……不过……」",
    "Script/scenario02_1.binu8@77006": "@vNanana_0018「……看的时候，我想和哥哥一起看。如果可以的话……还想牵着手……」",
    "Script/scenario02_1.binu8@77152": "@vNanana_0019「我才不是害怕呢！？」",
    "Script/scenario02_1.binu8@77280": "@vNanana_0020「哥哥太坏了——！！」",
    "Script/scenario02_1.binu8@77588": "@vKohaku_0247「早上好？现在已经是傍晚了哦。」",
    "Script/scenario02_1.binu8@77740": "@vKohaku_0248「原来如此。入乡随俗，对吧。……早上好。」",
    "Script/scenario02_1.binu8@78059": "@vMeguri_0096「是啊，早上好。从今天开始终于要全员合练了，真让人期待。」",
    "Script/scenario02_1.binu8@78303": "@vfutaba_0277「早、早上好。」",
    "Script/scenario02_1.binu8@78493": "@vfutaba_0278「练、练习是要做什么？练发声之类的吗？」",
    "Script/scenario02_1.binu8@78601": "@vMeguri_0097「呵呵呵，我们的训练会交给优秀的教官负责。相当严格的哦，加油吧。」",
    "Script/scenario02_1.binu8@78909": "@vrize_0020「抱歉，稍微来晚了一点。看来大家都已经到齐了，那就马上开始吧。」",
    "Script/scenario02_1.binu8@79057": "@vrize_0021「……你们真的要穿成这样吗？我倒不是说这样不行。」",
    "Script/scenario02_1.binu8@79190": "@vKohaku_0249「欸？」",
    "Script/scenario02_1.binu8@79220": "@vrize_0022「一年级和二年级的学生，不论有没有经验，首要任务都是提升基础体力。演剧是体力活，想要展现出好的演技，就得从锻炼身体开始。」",
    "Script/scenario02_1.binu8@79425": "@vrize_0023「首先做拉伸。然后一边跑步一边喊声。结束后还要做肌肉训练。舒展身体之后，再练习发声和吐字。」",
    "Script/scenario02_1.binu8@79663": "@vfutaba_0279「！？这是什么训练菜单！简直就是体育社团吧！」",
    "Script/scenario02_1.binu8@79792": "@vrize_0024「当然了。演剧本来就是体育系。身体太孱弱，可没法进行表现。对吧，濑和同学？」",
    "Script/scenario02_1.binu8@80125": "@vMeguri_0098「呵呵呵，要是能像座长和悠苑他们一样，拥有充足的体力和扎实的基础，就能免掉一部分训练。想练习演技，就先把基础打好吧。」",
    "Script/scenario02_1.binu8@80415": "@vrize_0025「……巡。很遗憾，不能有例外。基础训练你也必须参加。」",
    "Script/scenario02_1.binu8@80560": "@vMeguri_0099「啊、连我也要！？我的基础能力已经够好了吧！」",
    "Script/scenario02_1.binu8@80656": "@vrize_0026「不接受例外。这是前任座长的意思。」",
    "Script/scenario02_1.binu8@80904": "@vfutaba_0280「糟、糟糕了，环。我可没听说演剧是拼体力的！」",
    "Script/scenario02_1.binu8@81098": "@vKohaku_0250「环同学，你不和我们一起跑吗？」",
    "Script/scenario02_1.binu8@81226": "@vMeguri_0103「……别说那么见外的话。和我们一起痛痛快快地出身汗吧？」",
    "Script/scenario02_1.binu8@81390": "@voboro_0063「哈哈，大家都在等濑和同学呢。和濑和同学一起练习，果然更开心啊。」",
    "Script/scenario02_1.binu8@81865": "@vrize_0028「始终保持匀速！好好喊出声来！不许在舞台上耗尽体力！！」",
    "Script/scenario02_1.binu8@82016": "@vfutaba_0281「等、等一下……这、这不行……！！」",
    "Script/scenario02_1.binu8@82106": "@vMeguri_0104「呼、呼……好、好累……」",
    "Script/scenario02_1.binu8@82302": "@voboro_0064「箱鸟同学还真是干劲十足啊。说到底，她应该是因为濑和同学愿意来，所以很开心吧。」",
    "Script/scenario02_1.binu8@82833": "@vKohaku_0251「哈……哈、哈……！」",
    "Script/scenario02_1.binu8@83094": "@vrize_0029「真狡猾啊，真是的。」",
    "Script/scenario02_1.binu8@83143": "@vrize_0030「真正的天才，为什么能完美到这种地步啊。」",
    "Script/scenario02_1.binu8@83462": "@vrize_0031「……没什么。」",
    "Script/scenario02_1.binu8@83540": "@vrize_0032「既然要给出指示，我就觉得不亲自实践给大家看也没有意义。仅此而已，不多不少。」",
    "Script/scenario02_1.binu8@84200": "@vfutaba_0282「好、好辛苦啊……！！呼、呼……」",
    "Script/scenario02_1.binu8@84358": "@vKohaku_0252「完全不会！我最喜欢跑步了，反而觉得很开心。」",
    "Script/scenario02_1.binu8@84460": "@vMeguri_0105「……呵呵，还真是颇有收获的训练呢。」",
    "Script/scenario02_1.binu8@84704": "@vMeguri_0106「……我不是没有基础，只是不擅长长时间坚持而已。」",
    "Script/scenario02_1.binu8@85073": "@vrize_0033「今天的基础训练就到这里。明天开始也会继续进行，请做好心理准备再来排练场。」",
    "Script/scenario02_1.binu8@85248": "@vrize_0034「如果觉得太严格，我建议你尽早退出。演剧的世界可不是抱着天真的想法就能跟上的。」",
    "Script/scenario02_1.binu8@85444": "@vfutaba_0283「……咕、咕努努。」",
    "Script/scenario02_1.binu8@85613": "@vfutaba_0284「环！究竟要怎样才能增强体力啊！我不甘心！」",
    "Script/scenario02_1.binu8@85825": "@vfutaba_0285「咕努努努努……事到如今，只能彻底地跑、跑、拼命跑了……！我马上就开始，今晚就开始！！」",
    "Script/scenario02_1.binu8@86020": "@vrize_0035「到此为止。」",
    "Script/scenario02_1.binu8@86152": "@vrize_0036「让身体休息也是训练的一环。而且你已经完成了足够的基础训练，接下来该把时间用在别的事情上了。」",
    "Script/scenario02_1.binu8@86330": "@vfutaba_0286「可、可是……」",
    "Script/scenario02_1.binu8@86366": "@vrize_0037「一味埋头苦练，只会给身心积累压力。与其这样，不如去看看散落在世界各地的演剧，读读书，拓宽自己的世界。所有这些经历，最终都会连接到属于你自己的演剧上。」",
    "Script/scenario02_1.binu8@86664": "@vfutaba_0287「……原、原来如此……像我这样的人，就算着急也无济于事吧。」",
    "Script/scenario02_1.binu8@86790": "@vMeguri_0108「……基础固然重要，可我们也想练练演技嘛。」",
    "Script/scenario02_1.binu8@86886": "@vMeguri_0109「总是只练体力，也会腻的。奴隶嘛，得有像样的饵，才有干劲继续努力。」",
    "Script/scenario02_1.binu8@87045": "@voboro_0065「这方面应该不用担心。箱鸟同学肯定已经准备好了像样的奖励。」",
    "Script/scenario02_1.binu8@87191": "@vrize_0038「……从下周开始，基础训练结束后会进行简单的演技训练。不过，不知道那能不能称作奖励就是了。」",
    "Script/scenario02_1.binu8@87366": "@vKohaku_0253「啊，那我可期待了。」",
    "Script/scenario02_1.binu8@87470": "@vKohaku_0254「我早就想演点新东西了，已经有些按捺不住啦。」",
}


def polish(text: str) -> str:
    for source, target in REPLACEMENTS.items():
        text = text.replace(source, target)
    text = re.sub(r"[ \t]+(@[A-Za-z][A-Za-z0-9_]*)[ \t]+", r"\1", text)
    text = re.sub(r"[ \t]+(@[A-Za-z][A-Za-z0-9_]*)", r"\1", text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    args = parser.parse_args()
    with args.batch.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    for row in rows:
        row["translation"] = SCENE_OVERRIDES.get(row["id"], polish(row.get("translation", "")))
    with args.batch.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "translation"], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    print(f"polished={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
