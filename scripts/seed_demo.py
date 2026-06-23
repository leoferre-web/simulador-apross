import os
from datetime import date
from uuid import uuid4
from supabase import create_client

URL = os.environ.get('SUPABASE_URL')
KEY = os.environ.get('SUPABASE_KEY')
if not URL or not KEY:
    raise SystemExit('Setear SUPABASE_URL y SUPABASE_KEY como variables de entorno')

sb = create_client(URL, KEY)

troqueles = [
    {'codigo_troquel':'TRQ-10532','monodroga':'Trastuzumab','potencia':'440mg','forma_farmacologica':'ampolla','laboratorio':'Lab A','estado':'activa','pvp':120000,'fecha_vigencia_precio':str(date.today())},
    {'codigo_troquel':'TRQ-22980','monodroga':'Trastuzumab','potencia':'440mg','forma_farmacologica':'ampolla','laboratorio':'Lab B','estado':'activa','pvp':145000,'fecha_vigencia_precio':str(date.today())},
    {'codigo_troquel':'TRQ-30144','monodroga':'Trastuzumab','potencia':'440mg','forma_farmacologica':'ampolla','laboratorio':'Lab C','estado':'activa','pvp':98000,'fecha_vigencia_precio':str(date.today())},
    {'codigo_troquel':'TRQ-40021','monodroga':'Imatinib','potencia':'400mg','forma_farmacologica':'comprimido','laboratorio':'Lab D','estado':'activa','pvp':64000,'fecha_vigencia_precio':str(date.today())},
]
convenio = [
    {'codigo_troquel':'TRQ-10532','categoria':'Oncología y Ttos. Especiales','fecha_alta_convenio':str(date.today()),'fecha_baja_convenio':None},
    {'codigo_troquel':'TRQ-22980','categoria':'Oncología y Ttos. Especiales','fecha_alta_convenio':str(date.today()),'fecha_baja_convenio':None},
    {'codigo_troquel':'TRQ-40021','categoria':'Oncología y Ttos. Especiales','fecha_alta_convenio':str(date.today()),'fecha_baja_convenio':None},
]
liqs = []
for periodo in ['2026-01','2026-02','2026-03','2026-04','2026-05','2026-06']:
    for t in convenio:
        for i in range(1, 6):
            code = t['codigo_troquel']
            pvp_desc = next(x['pvp'] for x in troqueles if x['codigo_troquel'] == code) * 0.43
            liqs.append({'id_liquidacion':str(uuid4()), 'codigo_troquel':code, 'periodo':periodo, 'afiliado_id':f'AF-{i}', 'cantidad_cajas':1+i%2, 'pvp_remito':pvp_desc/0.43, 'pvp_descuento':pvp_desc})

for table, rows in [('troqueles', troqueles), ('convenio_oyte', convenio), ('liquidaciones', liqs)]:
    sb.table(table).upsert(rows).execute()
    print(f'Cargado {table}: {len(rows)} filas')
