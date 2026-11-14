"""Exact commands; unexpected words and negations are rejected."""
PHRASES={
 'джарвис':'open',
 'запусти камеру':'camera_on','включи камеру':'camera_on',
 'останови камеру':'camera_off','выключи камеру':'camera_off',
 'включи управление':'control_on','запусти управление':'control_on',
 'выключи управление':'control_off','останови управление':'control_off',
}
COMMANDS=frozenset(PHRASES.values())
GRAMMAR=list(PHRASES)+['джарвис '+phrase for phrase in PHRASES if phrase!='джарвис']+['[unk]']


def parse_command(result):
    words=result.get('result',[])
    if not isinstance(words,list) or not words:return None
    try:
        text=' '.join(str(word['word']).casefold() for word in words)
        confidence=[float(word.get('conf',0)) for word in words]
    except (KeyError,TypeError,ValueError,AttributeError):return None
    if min(confidence)<.55 or sum(confidence)/len(confidence)<.8:return None
    if text.startswith('джарвис '):text=text[len('джарвис '):]
    return PHRASES.get(text)
