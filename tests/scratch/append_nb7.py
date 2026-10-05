import json
p = r'C:\Users\santiago\Desktop\unal\analitica predictiva\std-santiago-ramos-galvis\PRE_08_series_de_tiempo\notebooks\notebook_7.ipynb'
nb = json.load(open(p, encoding='utf-8'))
nb['cells'].append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':[
 '#\n',
 '# Remove trend and cycle to make the series stationary\n',
 '#\n',
 'df_orig = functions.remove_trend_and_cycle(df_orig, yt_true_name="yt_true")\n',
 'df_orig.head(20)'
]})
json.dump(nb, open(p,'w',encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok', len(nb['cells']))
