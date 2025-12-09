from datetime import datetime

def construir_data_form(despacho):
    orden_recojo = [{
        "numeroRecojo": str(od["numero_recojo"]),
        "oc": {
            "codigo_producto": oc["producto"]["codigo_producto"],
            "producto": oc["producto"]["nombre_producto"],
            "proveedor": oc["producto"]["proveedor_marca"],
            "numero_oc": oc["numero_oc"],
            "precio_unitario": float(oc["precio_producto"]),
            "cantidad": oc["cantidad"],
        }
    } for od in despacho["ordenes_despacho"] for oc in [od["orden_compra"]]]

    return {
        "id_despacho": despacho["id"],
        "empresa": despacho["ordenes_compra"][0]["empresa"]["nombre_empresa"] if despacho["ordenes_compra"] else "",
        "proveedor": despacho["proveedor"]["nombre_proveedor"],
        "transportista": despacho["transportista"]["nombre_transportista"],
        "dua": despacho["dua"],
        "fechaNumeracion": despacho["fecha_numeracion"],
        "cartaPorte": despacho["carta_porte"],
        "numFactura": despacho["num_factura"],
        "fletePactado": despacho["flete_pactado"],
        "pesoNetoCrt": despacho["peso_neto_crt"],
        "ordenRecojo": orden_recojo
    }

def construir_data_table(detalles):
    tabla = []
    for detalle in detalles:
        estiba = detalle["pago_estiba"].lower()
        pago_estiba = 0.0 if "no" in estiba or "parcial" in estiba else 0.0
        tabla.append({
            "id_detalle": detalle["id"],
            "placa": detalle["placa_salida"],
            "sacosCargados": detalle["sacos_cargados"],
            "pesoSalida": detalle["peso_salida"],
            "placaLlegada": detalle["placa_llegada"],
            "sacosDescargados": detalle["sacos_descargados"],
            "pesoLlegada": detalle["peso_llegada"],
            "merma": detalle["merma"],
            "sacosFaltantes": detalle["sacos_faltantes"],
            "sacosRotos": detalle["sacos_rotos"],
            "sacosHumedos": detalle["sacos_humedos"],
            "sacosMojados": detalle["sacos_mojados"],
            "pagoEstiba": pago_estiba,
            "cantDesc": detalle["cant_desc"]
        })
    return tabla

def construir_data_extra(config, despacho):
    config = config[0] if config else {}
    otros_gastos = [{"descripcion": g["descripcion"], "monto": g["monto"]} for g in despacho.get("gastos_extra", [])]
    return {
        "fechaLlegada": datetime.strptime(despacho["fecha_llegada"], "%d/%m/%Y").isoformat() + "Z",
        "mermaPermitida": config.get("merma_permitida"),
        "precioProd": config.get("precio_prod"),
        "gastosNacionalizacion": config.get("gastos_nacionalizacion"),
        "margenFinanciero": config.get("margen_financiero"),
        "precioSacosRotos": config.get("precio_sacos_rotos"),
        "precioSacosHumedos": config.get("precio_sacos_humedos"),
        "precioSacosMojados": config.get("precio_sacos_mojados"),
        "tipoCambioDescExt": config.get("tipo_cambio_desc_ext"),
        "otrosGastos": otros_gastos
    }