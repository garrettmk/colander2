import React from "react";

class NewArgument extends React.Component {

    constructor (props) {
        super(props);

        this.handleInputChanged = this.handleInputChanged.bind(this);
        this.handleTypeChanged = this.handleTypeChanged.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);

        this.state = {
            input: '',
            type: 'scalar',
        }
    }

    handleInputChanged (e) {
        this.setState({
            input: e.target.value
        })
    }

    handleTypeChanged (e) {
        this.setState({
            type: e.target.value
        })
    }

    handleSubmit (e) {
        let value;

        switch (this.state.type) {
            case 'scalar':
                value = '';
                break;
            case 'list':
                value = [];
                break;
            case 'dict':
                value = {}
        }

        this.props.onSubmit(this.state.input, value);
    }

    render () {
        return (
            <span>
                <input
                    type="text"
                    value={this.state.input}
                    onChange={this.handleInputChanged}
                />
                <select value={this.state.type} onChange={this.handleTypeChanged}>
                    <option value="scalar">Value</option>
                    <option value="list">List</option>
                    <option value="dict">Dict</option>
                </select>
                <button onClick={this.handleSubmit}>Add</button>
            </span>
        )
    }
}

export default function Arguments (props) {

    const handleDataChanged = function (arg, value) {
        if (props.onDataChanged) {
            const asFloat = parseFloat(value);
            const asInt = parseInt(value);
            value = asFloat || asInt || value;
            let newData;

            if (props.data instanceof Array) {
                newData = props.data.slice();
                if (newData[arg] === undefined)
                    newData.push(value === '' ? arg : value);
                else
                    newData[arg] = value;
            } else {
                newData = Object.assign({}, props.data);
                newData[arg] = value;
            }

            props.onDataChanged(newData);
        }
    };

    const openChar = props.data instanceof Array ? '[' : '{';
    const closeChar = props.data instanceof Array ? ']' : '}'

    return (
        <div>
            <span>{openChar}</span>
            <ul>
                {Object.keys(props.data).map(arg => {
                    let val = props.data[arg];

                    if (typeof val === 'object')
                        return (
                            <li key={arg}>
                                {arg}:<br/>
                                <Arguments data={val} onDataChanged={newData => handleDataChanged(arg, newData)}/>
                            </li>
                        )
                    else
                        return (
                            <li key={arg}>
                                {arg}: <input
                                        type="text"
                                        value={val}
                                        onChange={e => handleDataChanged(arg, e.target.value)}
                                        />
                            </li>
                        )
                })}
                <li>
                    <NewArgument onSubmit={(name, data) => handleDataChanged(name, data)}/>
                </li>
            </ul>
            <span>{closeChar}</span>
        </div>
    )
}
