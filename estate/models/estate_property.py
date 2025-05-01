# -*- coding: utf-8 -*-

from odoo import models, fields
class EstateProperty(models.Model):
    _name = 'estate.property'
    _description = 'Real Estate Property'

    name= fields.Char(required=True)
    description= fields.Text()
    postcode= fields.Char()
    date_availability= fields.Date(default=fields.Date.today)
    expected_price= fields.Float(required=True)
    selling_price= fields.Float()
    bedrooms= fields.Integer()
    living_area= fields.Integer()
    facades= fields.Integer()
    garage= fields.Boolean()
    garden= fields.Boolean()
    garden_area= fields.Integer()
    garden_orientation= fields.Selection(string='Garden Orientation',
                                         selection=[('N', 'North'), ('S', 'South'), ('E', 'East'), ('W', 'West')],
                                         help='Orientation of the propery garden')