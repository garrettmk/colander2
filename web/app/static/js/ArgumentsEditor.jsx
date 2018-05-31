import React from "react";
import Arguments from "./Arguments";


export default class ArgumentsEditor extends React.Component {

    constructor (props) {
        super(props);

        this.handleDataChanged = this.handleDataChanged.bind(this);

        this.state = {
            data: props.data || {}
        }
    }

    handleDataChanged (newData) {
        this.setState({
            data: newData
        })
    }

    render () {
        return (
            <div>
                <Arguments data={this.state.data} onDataChanged={this.handleDataChanged}/>
                {JSON.stringify(this.state.data, null, 2)}
            </div>
        )
    }
}