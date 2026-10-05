import json
p = r'C:\Users\santiago\Desktop\unal\analitica predictiva\std-santiago-ramos-galvis\PRE_08_series_de_tiempo\notebooks\notebook_7.ipynb'
nb = json.load(open(p, encoding='utf-8'))
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Entrenamiento y pronostico\n',
 '#\n',
 'pipeline = create_pipeline()\n',
 'pipeline.fit(X_train, y_train)\n',
 'df_dropna[f"yt_d1d12_ar{p_max}"] = pipeline.predict(X_complete)\n',
 'df_orig.loc[df_dropna.index, f"yt_d1d12_ar{p_max}"] = df_dropna[f"yt_d1d12_ar{p_max}"]\n',
 'df_orig[["yt_true", "yt_true_d1d12", f"yt_d1d12_ar{p_max}"]].head(40)'
]})
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Integracion simple y estacional\n',
 '#\n',
 'import numpy as np  # type: ignore\n',
 '\n',
 'df_orig = df_orig.assign(yt_pred_d1d13_ar13=np.nan)\n',
 'df_orig.loc[df_dropna.index, "yt_pred_d1d13_ar13"] = df_dropna["yt_d1d12_ar13"]\n',
 'df_orig["yt_pred_d1d13_ar13"] += df_orig["yt_true"].shift(1)\n',
 'df_orig["yt_pred_d1d13_ar13"] += df_orig["yt_true"].shift(12)\n',
 'df_orig["yt_pred_d1d13_ar13"] -= df_orig["yt_true"].shift(13)\n',
 'df_orig[["yt_true", "yt_pred_d1d13_ar13"]].head(40)'
]})
json.dump(nb, open(p,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok', len(nb['cells']))
