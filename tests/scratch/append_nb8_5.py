import json
p = r'C:\Users\santiago\Desktop\unal\analitica predictiva\std-santiago-ramos-galvis\PRE_08_series_de_tiempo\notebooks\notebook_8.ipynb'
nb = json.load(open(p, encoding='utf-8'))
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Integracion simple y estacional\n',
 '#\n',
 'import numpy as np  # type: ignore\n',
 'df_orig = df_orig.assign(yt_pred_d1d12_mlp=np.nan)\n',
 'df_orig.loc[df_dropna.index, "yt_pred_d1d12_mlp"] = df_dropna["yt_d1d12_mlp"]\n',
 'df_orig["yt_pred_d1d12_mlp"] += df_orig["yt_true"].shift(1)\n',
 'df_orig["yt_pred_d1d12_mlp"] += df_orig["yt_true"].shift(12)\n',
 'df_orig["yt_pred_d1d12_mlp"] -= df_orig["yt_true"].shift(13)\n',
 'df_orig[["yt_true", "yt_pred_d1d12_mlp"]].head(40)'
]})
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Grafico de los pronosticos\n',
 '#\n',
 'functions.plot_time_series(df=df_orig, yt_col="yt_true")'
]})
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Almacenamiento de los resultados\n',
 '#\n',
 'functions.save_forecasts(df_orig)'
]})
json.dump(nb, open(p,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok', len(nb['cells']))
