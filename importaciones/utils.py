import hashlib
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
import os


def renderizar_template(template_path, data):
    """
    Renderiza la plantilla HTML con datos dinámicos.
    """
    # Configura el entorno de Jinja2
    env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
    template = env.get_template(os.path.basename(template_path))
    return template.render(data=data)

def convertir_html_a_pdf(html_content, output_path):
    """
    Convierte el contenido HTML en un archivo PDF.
    """
    with open(output_path, "wb") as output_file:
        pisa_status = pisa.CreatePDF(html_content, dest=output_file)
    return not pisa_status.err

def generar_pdf(template_path, output_path, data):
    """
    Genera un PDF a partir de una plantilla HTML y datos dinámicos.
    """
    # Renderiza el HTML con los datos
    html_content = renderizar_template(template_path, data)

    # Convierte el HTML a PDF
    exito = convertir_html_a_pdf(html_content, output_path)

    if exito:
        print(f"PDF generado exitosamente en: {output_path}")
    else:
        print("Hubo un error al generar el PDF.")

def calcular_monto_luego_dsctos_sacos(flete_base,total_descuento_sacos,total_descuento_por_dif_peso):
    result=flete_base-(total_descuento_sacos+total_descuento_por_dif_peso)
    return round(result,2)

def calcular_descuento_sacos(total_sacos_faltantes,total_sacos_rotos,total_sacos_humedos,total_sacos_mojados):
    return total_sacos_faltantes+total_sacos_rotos+total_sacos_humedos+total_sacos_mojados

def calcular_descuento_solo_sacos(total_sacos_rotos,total_sacos_humedos,total_sacos_mojados):
    return total_sacos_rotos+total_sacos_humedos+total_sacos_mojados

def calcular_monto_descuento_estiba(ref_base,cantidad, tipoCambio):
    """
    Calcula el monto de descuento para estiba basado en una regla de tres simple.

    Args:
        cantidad (int): La cantidad de sacos cargados.
        tipoCambio (float): El tipo de cambio para convertir el monto.

    Returns:
        float: El monto de descuento en la moneda correspondiente al tipo de cambio.
    """
    # Base para la regla de tres
    referencia_cantidad = ref_base
    referencia_descuento = 100  # Descuento en bolivianos para 560
    tipoCambio = float(tipoCambio)
    # Si la cantidad es exactamente igual a la referencia, usa directamente el valor
    if cantidad == referencia_cantidad:
        monto_descuento_moneda = (referencia_descuento / tipoCambio)/3
    else:
        # Aplicar regla de tres simple para otras cantidades
        total_descuento_bolivianos = cantidad * referencia_descuento / referencia_cantidad
        monto_descuento_moneda = (round(total_descuento_bolivianos,2) / tipoCambio)/3
    return round(monto_descuento_moneda, 2)

def calcular_monto_descuento_sacos_faltantes(cantidad_sacos_faltantes,precio_sacos_faltantes):
    return round(cantidad_sacos_faltantes*precio_sacos_faltantes,2)

def calcular_peso_no_considerado_por_sacos_faltante(cantidad_sacos_faltantes, peso_por_saco=None):
    if peso_por_saco  and peso_por_saco > 0:
        return abs(cantidad_sacos_faltantes) * peso_por_saco
    else:
        return abs(cantidad_sacos_faltantes) * 50

def calcular_diferencia_de_peso_por_cobrar_kg(diferencia_de_peso, merma_permitida, peso_sacos_faltantes):
    # Verificar si la diferencia de peso excede la merma permitida
    if diferencia_de_peso > merma_permitida:
        # Calcular la diferencia por cobrar
        diferencia_por_cobrar = diferencia_de_peso - merma_permitida
        # Restar el peso de los sacos faltantes si aplica
        diferencia_por_cobrar -= peso_sacos_faltantes
        # Asegurarnos de no devolver valores negativos
        return max(diferencia_por_cobrar, 0)
    else:
        # Si no excede la merma permitida, no se cobra nada
        return 0

def calcular_costo_por_kg(flete_pactado,precio_producto,margen_financiero,gastos_nac):


    # Cálculo del precio por tonelada
    precio_por_tonelada = precio_producto * 1000



    # Sumar flete pactado, margen financiero y gastos de nacionalización
    precio_bruto = precio_por_tonelada + flete_pactado + margen_financiero + gastos_nac

    # Calcular el IGV (18%) sobre el precio bruto
    igv = precio_bruto * 0.18

    # Calcular el precio final bruto sumando el IGV
    precio_bruto_final = precio_bruto + igv

    # calcular precio por TM
    precio_por_tonelada_final = round(precio_bruto_final / 1.18, 2)

    # Paso 2: Calcular el precio por kg
    precio_por_kg = round(precio_bruto_final / 1000, 4)

    data={
        "precio_por_tonelada":precio_por_tonelada,
        "precio_bruto":precio_bruto,
        "igv":igv,
        "precio_bruto_final":precio_bruto_final,
        "precio_por_tonelada_final":precio_por_tonelada_final,
        "precio_por_kg":precio_por_kg,
    }
    return data

def procesar_data_reporte(data):
    # Obtener los datos principales
    dataForm = data.get('dataForm', {})
    dataTable = data.get('dataTable', [])
    dataExtra = data.get('dataExtraForm', {})
    otrosGastos= dataExtra.get('otrosGastos',{})

    # Variables
    suma_peso_salida_kg = 0.00
    suma_peso_llegada_kg = 0.00
    total_sacos_cargados = 0
    total_sacos_descargados = 0
    total_sacos_faltantes = 0
    total_sacos_rotos = 0
    total_sacos_humedos = 0
    total_sacos_mojados = 0
    total_descuento_estiba = 0.00
    total_descuento_sacos=0.00
    total_descuento_solo_sacos = 0.00
    total_global_descuentos=0.00
    otros_gastos=0.00
    merma_total = 0.00
    pago_estiba_list = []
    empresa = ''

    fecha_numeracion=datetime.strptime(dataForm['fechaNumeracion'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%d/%m/%Y')

    if dataForm["empresa"] == "bd_trading_starsoft":
            empresa = "TRADING SEMILLA SAC"
    elif dataForm["empresa"] == "bd_semilla_starsoft":
            empresa = "LA SEMILLA SEMILLA DE ORO SAC"
    elif dataForm["empresa"] == "bd_maxi_starsoft":
            empresa = "MAXIMILIAN INVERSIONES SA"

    # Recorrer los datos de la tabla
    for item in dataTable:
        try:
            suma_peso_salida_kg += float(str(item["pesoSalida"]).replace(",", ""))
            suma_peso_llegada_kg += float(str(item["pesoLlegada"]).replace(",", ""))
            total_sacos_cargados += int(str(item["sacosCargados"]))
            total_sacos_descargados += int(str(item["sacosDescargados"]))
            merma_total += float(str(item["merma"]).replace(",", ""))
        except (ValueError, AttributeError) as e:
            print(f"Error procesando item: {item}, error: {e}")
        total_sacos_faltantes += int(item["sacosFaltantes"])
        total_sacos_rotos += int(item["sacosRotos"])  # Contar sacos rotos
        total_sacos_humedos += int(item["sacosHumedos"])  # Contar sacos húmedos
        total_sacos_mojados += int(item["sacosMojados"])  # Contar sacos mojado

        # Evaluar el valor de pagoEstiba
        pago_estiba_value = item.get("pagoEstiba")

        if pago_estiba_value is None:
            print(f"Advertencia: El campo 'pagoEstiba' está vacío para el item {item}")
            continue

        # Caso 1: "No pago 100 bolivianos"
        if "No pago estiba" in pago_estiba_value:
            # Concatenar placaLlegada y pagoEstiba
            # formatted_value = f"{item['placaLlegada']} - {pago_estiba_value}"
            # Agregar el resultado a la lista con un valor calculado
            pago_estiba_list.append({
                "placa": item['placaLlegada'],
                "detalle": pago_estiba_value,
                "monto_descuento": calcular_monto_descuento_estiba(item["sacosDescargados"],item["sacosDescargados"],dataExtra["tipoCambioDescExt"])
            })

        # Caso 2: "Pago parcial"
        elif "Pago parcial" in pago_estiba_value:
            pago_estiba_list.append({
                "placa": item['placaLlegada'],
                "detalle": f"No pago x {item['cantDesc']}",
                "monto_descuento": calcular_monto_descuento_estiba(item["sacosDescargados"],item["cantDesc"],dataExtra["tipoCambioDescExt"])
            })

    for item in pago_estiba_list:
        total_descuento_estiba += item['monto_descuento']

    datos_de_costo=calcular_costo_por_kg(dataForm["fletePactado"],dataExtra["precioProd"],dataExtra["margenFinanciero"],dataExtra["gastosNacionalizacion"])

    # Calcular la diferencia de peso (diferencia entre salida y llegada)
    diferencia_peso_kg = suma_peso_salida_kg - suma_peso_llegada_kg

    #calcula peso de sacos faltantes
    peso_sacos_faltantes=calcular_peso_no_considerado_por_sacos_faltante(total_sacos_faltantes)

    #calcula la diferencia de peso por cobrar teniendo en cuenta la merma permitida y la cantidad de sacos faltantes
    diferencia_peso_por_cobrar = calcular_diferencia_de_peso_por_cobrar_kg(diferencia_peso_kg, dataExtra["mermaPermitida"],peso_sacos_faltantes )


    # Calcular los descuentos por sacos dañados
    descuento_sacos_rotos = total_sacos_rotos * dataExtra["precioSacosRotos"]
    descuento_sacos_humedos = total_sacos_humedos * dataExtra["precioSacosHumedos"]
    descuento_sacos_mojados = total_sacos_mojados * dataExtra["precioSacosMojados"]

    # Precio base del flete (por tonelada)
    flete_base = dataForm["fletePactado"] * (dataForm["pesoNetoCrt"] / 1000)  # Convertir kg a toneladas

    # Cálculo del precio por tonelada
    precio_por_tonelada = dataExtra["precioProd"] * 1000

    # Sumar flete pactado, margen financiero y gastos de nacionalización
    precio_bruto = precio_por_tonelada + dataForm["fletePactado"] + dataExtra["margenFinanciero"] + dataExtra[
        "gastosNacionalizacion"]

    # Calcular el IGV (18%) sobre el precio bruto
    igv = datos_de_costo.get("igv")

    # Calcular el precio final bruto sumando el IGV
    precio_bruto_final = precio_bruto + igv

    # calcular precio por TM
    precio_por_tonelada_final=round(precio_bruto_final/1.18,2)

    # Paso 2: Calcular el precio por kg
    precio_por_kg = round(precio_bruto_final/1000,5)

    # calcular descuento por sacos faltantes
    total_descuento_sacos_faltantes = round(peso_sacos_faltantes * precio_por_kg,2)



    total_descuento_sacos = calcular_descuento_sacos(total_descuento_sacos_faltantes,descuento_sacos_rotos,descuento_sacos_humedos,descuento_sacos_mojados)

    total_descuento_solo_sacos=calcular_descuento_solo_sacos(descuento_sacos_rotos,descuento_sacos_humedos,descuento_sacos_mojados)

    pago_final = flete_base - total_descuento_sacos

    # Paso 3: Calcular el descuento por diferencia de peso
    # Si la diferencia de peso por cobrar es positiva, calculamos el descuento
    if diferencia_peso_por_cobrar and diferencia_peso_por_cobrar > 0:
        descuento_por_diferencia_peso = diferencia_peso_por_cobrar * precio_por_kg
    else:
        descuento_por_diferencia_peso = 0  # No hay descuento si no hay diferencia de peso

    # Si hay diferencia de peso por cobrar, sumamos al pago final el monto correspondiente
    if diferencia_peso_por_cobrar and diferencia_peso_por_cobrar > 0:
        pago_final -= descuento_por_diferencia_peso

    # Si hay descuento por pago de estiba
    if total_descuento_estiba and total_descuento_estiba > 0:
        pago_final -= total_descuento_estiba

    #si hay descuento por sacos faltantes:
    if total_descuento_sacos and total_descuento_sacos > 0:
        pago_final -=total_descuento_sacos

    aux_descuento = descuento_por_diferencia_peso + total_descuento_sacos_faltantes + descuento_sacos_rotos + descuento_sacos_humedos + descuento_sacos_mojados

    for item in otrosGastos:
        otros_gastos+=item.get('monto',0.00)

    tota_dsct_sin_gastos_otros=round((descuento_por_diferencia_peso + total_descuento_estiba + total_descuento_sacos_faltantes + descuento_sacos_rotos + descuento_sacos_humedos + descuento_sacos_mojados ),2)

    total_dsct= round((descuento_por_diferencia_peso + total_descuento_estiba + total_descuento_sacos_faltantes + descuento_sacos_rotos + descuento_sacos_humedos + descuento_sacos_mojados + otros_gastos),2)

    total_a_pagar= round(flete_base-total_dsct,2)

    total_global_descuentos = round(total_descuento_sacos + total_descuento_estiba + descuento_por_diferencia_peso,2)

    data_procesada={
        "dataForm":dataForm,
        "dataTable":dataTable,
        "dataExtra":dataExtra,
        "procesado": {
            "suma_peso_salida": suma_peso_salida_kg,
            "suma_peso_llegada": suma_peso_llegada_kg,
            "total_sacos_cargados": total_sacos_cargados,
            "total_sacos_descargados": total_sacos_descargados,
            "total_sacos_faltantes": total_sacos_faltantes,
            "total_sacos_rotos": total_sacos_rotos,
            "total_sacos_humedos": total_sacos_humedos,
            "total_sacos_mojados": total_sacos_mojados,
            "total_descuento_estiba": total_descuento_estiba,
            "aux_descuento":aux_descuento,
            "merma_total": merma_total,
            "diferencia_de_peso":diferencia_peso_kg ,
            'descuento_peso_sacos_faltantes':peso_sacos_faltantes,
            "diferencia_peso_por_cobrar":diferencia_peso_por_cobrar,
            "descuento_por_diferencia_peso":descuento_por_diferencia_peso,
            "descuento_sacos_faltantes": total_descuento_sacos_faltantes,
            "descuento_sacos_rotos": descuento_sacos_rotos,
            "descuento_sacos_humedos":descuento_sacos_humedos,
            "descuento_sacos_mojados":descuento_sacos_mojados,
            "total_descuento_sacos":total_descuento_sacos,
            "tota_dsct_sin_gastos_otros": tota_dsct_sin_gastos_otros,
            "total_descuento_solo_sacos": total_descuento_solo_sacos,
            "total_luego_dsctos_sacos":calcular_monto_luego_dsctos_sacos(flete_base,total_descuento_sacos,descuento_por_diferencia_peso),
            "total_global_descuentos":total_global_descuentos,
            "precio_por_tonelada":round(precio_por_tonelada,2),
            "precio_bruto_final":round(precio_bruto_final,2),
            "precio_por_tonelada_final": precio_por_tonelada_final,
            "precio_por_kg_final":precio_por_kg,
            "pago_final":round(pago_final,2),
            "pago_estiba_list": tuple(pago_estiba_list),
            "otros_gastos":tuple(otrosGastos),
            "total_otros_gastos":otros_gastos,
            "igv":round(igv,2),
            "flete_base":round(flete_base,2),
            "empresa": empresa,
            "fecha_numeracion":fecha_numeracion,
            "len_tabla": len(dataTable),
            "len_tabla_one_more":len(dataTable)+1,
            "len_tabla_two_more": len(dataTable)+2,
            "total_dsct":total_dsct,
            "total_a_pagar":total_a_pagar
        }
    }

    return data_procesada

def procesar_data_bd_reporte(data):
    aux=data[0]
    data_extra=aux.get('configuracion_despacho',[])[0]
    detalle_despacho=aux.get('detalle_despacho', [])
    ocs = aux.get('ordenes_compra')
    ocsd=aux.get('ordenes_despacho')
    ordenRecojo = []
    numerosRecojo = []  # Lista para almacenar los números de recojo

    for item in ocsd:
        numerosRecojo.append(str(item["numero_recojo"]))  # Convertir a string y almacenar
        ordenRecojo.append({
            "oc": {
                "numero_oc": item["orden_compra"]["numero_oc"],
                "producto": item["orden_compra"]["producto"]["nombre_producto"],
                "codigo_producto": item["orden_compra"]["producto"]["codigo_producto"],
                "cantidad": item["orden_compra"]["cantidad"],
                "unidad_medida": "KG",
                "precio_unitario": float(item["orden_compra"]["precio_producto"]),
                "precio_total": float(item["orden_compra"]["precio_producto"]) * item["orden_compra"]["cantidad"],
                "proveedor": item["orden_compra"]["producto"]["proveedor_marca"],
                "codprovee": "123366014"
            },
            "numeroRecojo": item["numero_recojo"]
        })



    # Concatenar los números de recojo separados por comas
    numRecojo = ",".join(numerosRecojo)

    dataForm = {
        "empresa": aux.get('ordenes_compra')[0].get('empresa').get('nombre_empresa'),
        "oc": [item["numero_oc"] for item in ocs if "numero_oc" in item],
        "producto": aux.get('ordenes_compra')[0].get('producto').get('nombre_producto'),
        "precioProducto": aux.get('ordenes_compra')[0].get('precio_producto'),
        "ordenRecojo": ordenRecojo,
        "proveedor": aux.get('proveedor').get('nombre_proveedor'),
        "dua": aux.get('dua'),
        "numRecojo": numRecojo,
        "fechaNumeracion": aux.get('fecha_numeracion'),
        "cartaPorte": aux.get('carta_porte'),
        "numFactura": aux.get('num_factura'),
        "transportista": aux.get('transportista').get("nombre_transportista"),
        "fletePactado": aux.get('flete_pactado'),
        "pesoNetoCrt": aux.get('peso_neto_crt')
    }

    dataExtra={
      "mermaPermitida": data_extra.get('merma_permitida'),
      "precioProd": data_extra.get('precio_prod'),
      "gastosNacionalizacion": data_extra.get('gastos_nacionalizacion'),
      "margenFinanciero": data_extra.get('margen_financiero'),
      "precioSacosRotos": data_extra.get('precio_sacos_rotos'),
      "precioSacosHumedos": data_extra.get('precio_sacos_humedos'),
      "precioSacosMojados": data_extra.get('precio_sacos_mojados'),
      "tipoCambioDescExt": data_extra.get('tipo_cambio_desc_ext'),
      "fechaLlegada": aux.get('fecha_llegada'),
      "otrosGastos":aux.get('gastos_extra',[])
    }

    dataTable  = [
        {
            "numero": idx + 1,
            "placa": item["placa_salida"],
            "sacosCargados": item["sacos_cargados"],
            "pesoSalida": float(item["peso_salida"]),  # Convertir a float
            "placaLlegada": item["placa_llegada"],
            "sacosDescargados": item["sacos_descargados"],
            "pesoLlegada": float(item["peso_llegada"]),  # Convertir a float
            "merma": float(item["merma"]),  # Convertir a float
            "sacosFaltantes": item["sacos_faltantes"],
            "sacosRotos": item["sacos_rotos"],
            "sacosHumedos": item["sacos_humedos"],
            "sacosMojados": item["sacos_mojados"],
            "pagoEstiba": item["pago_estiba"],
            "cantDesc": item["cant_desc"]
        }
        for idx, item in enumerate(detalle_despacho)
    ]

    otrosGastos= dataExtra.get('otrosGastos',{})

    # Variables
    suma_peso_salida_kg = 0.00
    suma_peso_llegada_kg = 0.00
    total_sacos_cargados = 0
    total_sacos_descargados = 0
    total_sacos_faltantes = 0
    total_sacos_rotos = 0
    total_sacos_humedos = 0
    total_sacos_mojados = 0
    total_descuento_estiba = 0.00
    total_descuento_sacos = 0.00
    total_descuento_solo_sacos = 0.00
    total_global_descuentos = 0.00
    otros_gastos = 0.00
    merma_total = 0.00
    pago_estiba_list = []
    empresa = ''

    fecha_str = dataForm['fechaNumeracion'].rsplit('-', 1)[0]  # Quita el offset '-05:00'
    fecha_numeracion = datetime.strptime(fecha_str, '%Y-%m-%dT%H:%M:%S').strftime('%d/%m/%Y')
    if dataForm["empresa"] == "bd_trading_starsoft":
        empresa = "TRADING SEMILLA SAC"
    elif dataForm["empresa"] == "bd_semilla_starsoft":
        empresa = "LA SEMILLA SEMILLA DE ORO SAC"
    elif dataForm["empresa"] == "bd_maxi_starsoft":
        empresa = "MAXIMILIAN INVERSIONES SA"


    # Recorrer los datos de la tabla
    for item in dataTable:

        try:
            suma_peso_salida_kg += float(str(item["pesoSalida"]).replace(",", ""))
            suma_peso_llegada_kg += float(str(item["pesoLlegada"]).replace(",", ""))
            total_sacos_cargados += int(str(item["sacosCargados"]))
            total_sacos_descargados += int(str(item["sacosDescargados"]))
            merma_total += float(str(item["merma"]).replace(",", ""))
        except (ValueError, AttributeError) as e:
            print(f"Error procesando item: {item}, error: {e}")
        total_sacos_faltantes += int(item["sacosFaltantes"])
        total_sacos_rotos += int(item["sacosRotos"])  # Contar sacos rotos
        total_sacos_humedos += int(item["sacosHumedos"])  # Contar sacos húmedos
        total_sacos_mojados += int(item["sacosMojados"])  # Contar sacos mojado

        # Evaluar el valor de pagoEstiba
        pago_estiba_value = item.get("pagoEstiba")

        if pago_estiba_value is None:
            print(f"Advertencia: El campo 'pagoEstiba' está vacío para el item {item}")
            continue

        # Caso 1: "No pago 100 bolivianos"
        if "No pago estiba" in pago_estiba_value:
            # Concatenar placaLlegada y pagoEstiba
            # formatted_value = f"{item['placaLlegada']} - {pago_estiba_value}"
            # Agregar el resultado a la lista con un valor calculado
            pago_estiba_list.append({
                "placa": item['placaLlegada'],
                "detalle": pago_estiba_value,
                "monto_descuento": calcular_monto_descuento_estiba(item["sacosDescargados"], item["sacosDescargados"],
                                                                   dataExtra["tipoCambioDescExt"])
            })

        # Caso 2: "Pago parcial"
        elif "Pago parcial" in pago_estiba_value:
            pago_estiba_list.append({
                "placa": item['placaLlegada'],
                "detalle": f"No pago x {item['cantDesc']}",
                "monto_descuento": calcular_monto_descuento_estiba(item["sacosDescargados"], item["cantDesc"],
                                                                   dataExtra["tipoCambioDescExt"])
            })

    for item in pago_estiba_list:
        total_descuento_estiba += item['monto_descuento']


    datos_de_costo = calcular_costo_por_kg(float(dataForm["fletePactado"]), float(dataExtra["precioProd"]),
                                           float(dataExtra["margenFinanciero"]), float(dataExtra["gastosNacionalizacion"]))

    # Calcular la diferencia de peso (diferencia entre salida y llegada)
    diferencia_peso_kg = suma_peso_salida_kg - suma_peso_llegada_kg

    # calcula peso de sacos faltantes
    peso_sacos_faltantes = calcular_peso_no_considerado_por_sacos_faltante(total_sacos_faltantes)



    # calcula la diferencia de peso por cobrar teniendo en cuenta la merma permitida y la cantidad de sacos faltantes
    diferencia_peso_por_cobrar = calcular_diferencia_de_peso_por_cobrar_kg(diferencia_peso_kg,
                                                                           float(dataExtra["mermaPermitida"]),
                                                                           peso_sacos_faltantes)

    # Calcular los descuentos por sacos dañados
    descuento_sacos_rotos = total_sacos_rotos * dataExtra["precioSacosRotos"]
    descuento_sacos_humedos = total_sacos_humedos * dataExtra["precioSacosHumedos"]
    descuento_sacos_mojados = total_sacos_mojados * dataExtra["precioSacosMojados"]

    peso_neto=float(dataForm["pesoNetoCrt"])
    # Precio base del flete (por tonelada)
    flete_base = dataForm["fletePactado"] * (peso_neto / 1000)  # Convertir kg a toneladas

    # Cálculo del precio por tonelada
    precio_por_tonelada = dataExtra["precioProd"] * 1000

    # Sumar flete pactado, margen financiero y gastos de nacionalización


    precio_bruto = precio_por_tonelada + dataForm["fletePactado"] + dataExtra["margenFinanciero"] + dataExtra[
        "gastosNacionalizacion"]

    # Calcular el IGV (18%) sobre el precio bruto
    igv = datos_de_costo.get("igv")

    # Calcular el precio final bruto sumando el IGV
    precio_bruto_final = precio_bruto + igv

    # calcular precio por TM
    precio_por_tonelada_final = round(precio_bruto_final / 1.18, 2)

    # Paso 2: Calcular el precio por kg
    precio_por_kg = round(precio_bruto_final / 1000, 4)

    # calcular descuento por sacos faltantes
    total_descuento_sacos_faltantes = round(peso_sacos_faltantes * precio_por_kg, 2)

    total_descuento_sacos = calcular_descuento_sacos(total_descuento_sacos_faltantes, descuento_sacos_rotos,
                                                     descuento_sacos_humedos, descuento_sacos_mojados)

    total_descuento_solo_sacos = calcular_descuento_solo_sacos(descuento_sacos_rotos, descuento_sacos_humedos,
                                                               descuento_sacos_mojados)

    pago_final = flete_base - total_descuento_sacos

    # Paso 3: Calcular el descuento por diferencia de peso
    # Si la diferencia de peso por cobrar es positiva, calculamos el descuento
    if diferencia_peso_por_cobrar and diferencia_peso_por_cobrar > 0:
        descuento_por_diferencia_peso = diferencia_peso_por_cobrar * precio_por_kg
    else:
        descuento_por_diferencia_peso = 0  # No hay descuento si no hay diferencia de peso

    # Si hay diferencia de peso por cobrar, sumamos al pago final el monto correspondiente
    if diferencia_peso_por_cobrar and diferencia_peso_por_cobrar > 0:
        pago_final -= descuento_por_diferencia_peso

    # Si hay descuento por pago de estiba
    if total_descuento_estiba and total_descuento_estiba > 0:
        pago_final -= total_descuento_estiba

    # si hay descuento por sacos faltantes:
    if total_descuento_sacos and total_descuento_sacos > 0:
        pago_final -= total_descuento_sacos

    aux_descuento = descuento_por_diferencia_peso + total_descuento_sacos_faltantes + descuento_sacos_rotos + descuento_sacos_humedos + descuento_sacos_mojados

    for item in otrosGastos:
        otros_gastos += item.get('monto', 0.00)

    tota_dsct_sin_gastos_otros = round((
                                                   descuento_por_diferencia_peso + total_descuento_estiba + total_descuento_sacos_faltantes + descuento_sacos_rotos + descuento_sacos_humedos + descuento_sacos_mojados),
                                       2)

    total_dsct = round((
                                   descuento_por_diferencia_peso + total_descuento_estiba + total_descuento_sacos_faltantes + descuento_sacos_rotos + descuento_sacos_humedos + descuento_sacos_mojados + otros_gastos),
                       2)

    total_a_pagar = round(flete_base - total_dsct, 2)

    total_global_descuentos = round(total_descuento_sacos + total_descuento_estiba + descuento_por_diferencia_peso, 2)

    data_procesada = {
        "dataForm": dataForm,
        "dataTable": dataTable,
        "dataExtra": dataExtra,
        "procesado": {
            "suma_peso_salida": suma_peso_salida_kg,
            "suma_peso_llegada": suma_peso_llegada_kg,
            "total_sacos_cargados": total_sacos_cargados,
            "total_sacos_descargados": total_sacos_descargados,
            "total_sacos_faltantes": total_sacos_faltantes,
            "total_sacos_rotos": total_sacos_rotos,
            "total_sacos_humedos": total_sacos_humedos,
            "total_sacos_mojados": total_sacos_mojados,
            "total_descuento_estiba": total_descuento_estiba,
            "aux_descuento": aux_descuento,
            "merma_total": merma_total,
            "diferencia_de_peso": diferencia_peso_kg,
            'descuento_peso_sacos_faltantes': peso_sacos_faltantes,
            "diferencia_peso_por_cobrar": diferencia_peso_por_cobrar,
            "descuento_por_diferencia_peso": descuento_por_diferencia_peso,
            "descuento_sacos_faltantes": total_descuento_sacos_faltantes,
            "descuento_sacos_rotos": descuento_sacos_rotos,
            "descuento_sacos_humedos": descuento_sacos_humedos,
            "descuento_sacos_mojados": descuento_sacos_mojados,
            "total_descuento_sacos": total_descuento_sacos,
            "tota_dsct_sin_gastos_otros": tota_dsct_sin_gastos_otros,
            "total_descuento_solo_sacos": total_descuento_solo_sacos,
            "total_luego_dsctos_sacos": calcular_monto_luego_dsctos_sacos(flete_base, total_descuento_sacos,
                                                                          descuento_por_diferencia_peso),
            "total_global_descuentos": total_global_descuentos,
            "precio_por_tonelada": round(precio_por_tonelada, 2),
            "precio_bruto_final": round(precio_bruto_final, 2),
            "precio_por_tonelada_final": precio_por_tonelada_final,
            "precio_por_kg_final": precio_por_kg,
            "pago_final": round(pago_final, 2),
            "pago_estiba_list": tuple(pago_estiba_list),
            "otros_gastos": tuple(otrosGastos),
            "total_otros_gastos": otros_gastos,
            "igv": round(igv, 2),
            "flete_base": round(flete_base, 2),
            "empresa": empresa,
            "fecha_numeracion": fecha_numeracion,
            "len_tabla": len(dataTable),
            "len_tabla_one_more": len(dataTable) + 1,
            "len_tabla_two_more": len(dataTable) + 2,
            "total_dsct": total_dsct,
            "total_a_pagar": total_a_pagar
        }
    }

    return data_procesada

def calcular_hash_archivo(file_obj):
    sha256 = hashlib.sha256()
    for chunk in file_obj.chunks():
        sha256.update(chunk)
    return sha256.hexdigest()