import React from "react";
import Arguments from "./Arguments";


export default class ExtensionAction extends React.Component {

    // module, actions
    constructor (props) {
        super(props);

        this.handleActionChange = this.handleActionChange.bind(this);
        this.handleArgumentsChange = this.handleArgumentsChange.bind(this);
        this.handleKwargsChange = this.handleKwargsChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleClear = this.handleClear.bind(this);

        this.state = {
            module: props.module,
            action: props.actions ? props.actions[0] : '',
            args: [],
            kwargs: {},
            status: undefined
        }
    }

    handleActionChange (e) {
        const newAction = e.target.value;
        this.setState(currentState => {
            return { action: newAction }
        });
    }

    handleArgumentsChange (newArgs) {
        this.setState(currentState => {
            return { args: newArgs }
        });
    }

    handleKwargsChange (newKwargs) {
        this.setState(currentState => {
            return { kwargs: newKwargs }
        });
    }

    handleSubmit () {
        if (this.props.onSubmit)
            this.props.onSubmit(this.state)
    }

    handleClear () {
        this.setState({})
    }

    render () {
        return (
            <div className={"outlined"}>
                <h4>Extension: {this.props.name}</h4>
                <table>
                    <tbody>
                        <tr>
                            <td>
                                <div>
                                    <h6>Action</h6>
                                    <select value={this.state.action} onChange={this.handleActionChange}>
                                        {this.props.actions.map(action => (
                                            <option key={action} value={action}>{action}</option>
                                        ))}
                                    </select>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div>
                                    <h6>Arguments</h6>
                                    <Arguments data={this.state.args} onDataChanged={this.handleArgumentsChange}/>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div>
                                    <h6>Parameters</h6>
                                    <Arguments data={this.state.kwargs} onDataChanged={this.handleKwargsChange}/>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <button onClick={this.handleSubmit}>Send</button>
                                <button onClick={this.handleClear}>Clear</button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        )
    }
}
