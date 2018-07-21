import React from "react";
import ObjectTable from "./ObjectTable"


export default function ExtensionsList (props) {
    return ObjectTable({
        title: 'Extensions',
        fields: {
            ID: 'id',
            Module: 'module',
            Name: 'Name'
        },
        linkOnAttr: 'id',
        linkPrefix: '/extensions/',
        loading: props.loading,
        total: props.total,
        objects: props.extensions,
        page: props.page,
        pages: props.pages,
        onNextPage: props.onNextPage,
        onPrevPage: props.onPrevPage
    })
}