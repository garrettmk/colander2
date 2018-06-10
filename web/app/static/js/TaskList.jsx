import React from "react";
import ObjectTable from "./ObjectTable";


export default class TaskList extends React.Component {

    constructor (props) {
        super(props);
    }

    render () {
        return ObjectTable({
            title: 'Tasks',
            fields: {
                ID: 'id',
                Name: 'name',
                Module: 'module',
                Action: 'action',
                Args: 'args',
                Kwargs: 'kwargs',
            }
        })
    }
}