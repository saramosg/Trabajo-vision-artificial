import json
p = r'C:\Users\santiago\Desktop\unal\analitica predictiva\std-santiago-ramos-galvis\PRE_08_series_de_tiempo\notebooks\notebook_7.ipynb'
nb = json.load(open(p, encoding='utf-8'))
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
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Metricas de error\n',
 '#\n',
 'metrics = functions.compute_evaluation_metrics(df_orig.dropna())\n',
 'functions.save_metrics(metrics)\n',
 'metrics'
]})
json.dump(nb, open(p,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok', len(nb['cells']))
