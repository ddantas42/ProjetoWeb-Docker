import json

def loadLang(lang):

	if (lang == 'es'):
		with open('site/lang/es.json', encoding='utf-8') as f:
			data = json.load(f)
			f.close()

	elif (lang == 'fr'):
		with open('site/lang/fr.json', encoding='utf-8') as f:
			data = json.load(f)
			f.close()

	elif (lang == 'pt'):
		with open('site/lang/pt.json', encoding='utf-8') as f:
			data = json.load(f)
			f.close()

	else:
		with open('site/lang/en.json', encoding='utf-8') as f:
			data = json.load(f)
			f.close()

	return data


def loadSpecialLang(lang, type):
	data = loadLang(lang)
	return data['special'][type]