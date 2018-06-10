import React from "react";
import ObjectTable from "./ObjectTable";


export default function VendorsList (props) {
    return ObjectTable({
        title: 'Vendors',
        fields: {
            ID: 'id',
            Name: 'name',
            Website: 'url'
        },
        linkOnAttr: 'name',
        linkPrefix: '/vendors/',
        loading: props.loading,
        total: props.total,
        objects: props.vendors,
        page: props.page,
        pages: props.pages,
        onNextPage: props.onNextPage,
        onPrevPage: props.onPrevPage
    })
}
