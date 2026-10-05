import json
p = r'C:\Users\santiago\Desktop\unal\analitica predictiva\std-santiago-ramos-galvis\PRE_08_series_de_tiempo\notebooks\notebook_7.ipynb'
nb = json.load(open(p, encoding='utf-8'))
nb['cells'] = [
    {'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':['import nbimporter #type: ignore']},
    {'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
        '# ============================================================\n',
        '# Pronostico usando un modelo autorregresivo\n',
        '# ============================================================\n',
        'import warnings\n',
        '\n',
        'warnings.filterwarnings("ignore")\n',
        '\n',
        '#\n',
        '# Carga de datos\n',
        '#\n',
        'import functions  # type: ignore\n',
        '\n',
        'df_orig = functions.load_data()\n',
        'df_orig.head()'
    ]},
]
json.dump(nb, open(p,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok', len(nb['cells']))
