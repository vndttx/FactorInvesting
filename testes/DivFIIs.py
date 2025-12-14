pip install fundamentus
import fundamentus

detalhes_fii = fundamentus.get_detalhes_fii('MXRF11')

print(f"Informações para o FII MXRF11:")
print(f"Preço: R$ {detalhes_fii.iloc[0]['cotacao']}")
print(f"Dividend Yield (12M): {detalhes_fii.iloc[0]['dy']}%")
print(f"P/VP: {detalhes_fii.iloc[0]['p_v']}")
