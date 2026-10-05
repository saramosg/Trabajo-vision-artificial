import json
p = r'C:\Users\santiago\Desktop\unal\analitica predictiva\std-santiago-ramos-galvis\PRE_08_series_de_tiempo\notebooks\notebook_9.ipynb'
nb = json.load(open(p, encoding='utf-8'))
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Promedio de los pronosticos\n',
 '#\n',
 'from sklearn.linear_model import LinearRegression\n',
 '\n',
 'model = LinearRegression()\n',
 'X = df_dropna.drop(columns=["yt_true", "yt_pred_mean"])\n',
 'y = df_dropna["yt_true"]\n',
 'model.fit(X, y)\n',
 'df_dropna["yt_pred_lr"] = model.predict(X)\n',
 'functions.plot_time_series(df=df_dropna[["yt_true", "yt_pred_lr"]], yt_col="yt_true")'
]})
json.dump(nb, open(p,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok', len(nb['cells']))
