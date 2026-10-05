import json
p = r'C:\Users\santiago\Desktop\unal\analitica predictiva\std-santiago-ramos-galvis\PRE_08_series_de_tiempo\notebooks\notebook_9.ipynb'
nb = json.load(open(p, encoding='utf-8'))
nb['cells'] = [
    {'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':['import nbimporter  # type: ignore']},
    {'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
        '# ============================================================\n',
        '# Combinacion de pronosticos\n',
        '# ============================================================\n',
        'import warnings\n',
        '\n',
        'warnings.filterwarnings("ignore")\n',
        '\n',
        '#\n',
        '# Carga de datos\n',
        '#\n',
        'import functions  # type: ignore\n',
        'import pandas as pd  # type: ignore\n',
        '\n',
        '#\n',
        '# Promedio de los pronosticos\n',
        '#\n',
        'df_orig = pd.read_csv("../submission/forecasts.csv")\n',
        'df_dropna = df_orig.dropna()\n',
        'df_dropna = df_dropna.set_index("date")\n',
        'df_dropna["yt_pred_mean"] = df_dropna.mean(axis=1)\n',
        'functions.plot_time_series(df=df_dropna[["yt_true", "yt_pred_mean"]], yt_col="yt_true")'
    ]},
]
json.dump(nb, open(p,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok', len(nb['cells']))
