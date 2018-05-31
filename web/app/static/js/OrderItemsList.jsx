import React from "react";
import ObjectTable from "./ObjectTable"


export default function ListingsList (props) {
    return ObjectTable({
        title: 'Listings',
        fields: {
            ID: 'id',
            Vendor: 'vendor_id',
            SKU: 'sku',
            Title: 'title'
        },
        loading: props.loading,
        total: props.total,
        objects: props.listings
    })
}