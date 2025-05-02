# -*- coding: utf-8 -*-
from odoo import fields, models



class EstateProperty(models.Model):
    _name = "maquinas.property"
    _description = "Estado Máquinas"



    name=fields.Char("Nombre Maquina",required=True)
    description=fields.Text("Description",copy=False)
    fuelLevel=fields.Selection(
        selection=[("0%","0%"),
                   ("10%","10%"),
                   ("20%","20%"),
                   ("30%","30%"),
                   ("40%","40%"),
                   ("50%","50%"),
                   ("60%","60%"),
                   ("70%","70%"),
                   ("80%","80%"),
                   ("90%","90%"),
                   ("100%","100%")],
        string="Nivel de combustible",
        required=True
        copy=False,
        default="100%",
    )
    place=fields.Char("Lugar donde se encuentra",required=True)
