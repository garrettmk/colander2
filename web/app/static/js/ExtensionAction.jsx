import React from "react";
import Arguments from "./Arguments";
import ArgumentsEditor from "./ArgumentsEditor";


export default class ExtensionAction extends React.Component {

    constructor (props) {
        super(props);

        this.handleActionChange = this.handleActionChange.bind(this);
        this.handleArgumentsChange = this.handleArgumentsChange.bind(this);
        this.handleKwargsChange = this.handleKwargsChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleClear = this.handleClear.bind(this);

        this.state = {
            actions: props.actions || ['first', 'second', 'third'],
            action: '',
            args: [],
            kwargs: {}
        }
    }

    handleActionChange (e) {
        this.setState({
            action: e.target.value
        })
    }

    handleArgumentsChange (newArgs) {
        this.setState({
            args: newArgs
        })
    }

    handleKwargsChange (newKwargs) {
        this.setState({
            kwargs: newKwargs
        })
    }

    handleSubmit () {
        console.log(this.state)
        if (this.props.onSubmit)
            this.props.onSubmit({
                action: this.state.action,
                args: this.state.args,
                kwargs: this.state.kwargs
            })
    }

    handleClear () {
        this.setState({
            args: [],
            kwargs: {}
        })
    }

    render () {
        return (
            <table style={{ borderStyle: 'solid', borderWidth: '5px'}}>
                <tbody>
                    <tr>
                        <td>
                            <div>
                                <h6>Action</h6>
                                <select value={this.state.action} onChange={this.handleActionChange}>
                                    {this.state.actions.map(action => (
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
        )
    }
}
