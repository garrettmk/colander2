import React from "react";
import Arguments from "./Arguments";


export default class ExtensionAction extends React.Component {

    // vendorId
    constructor (props) {
        super(props);

        this.fetchExtension = this.fetchExtension.bind(this);
        this.sendExtAction = this.sendExtAction.bind(this);
        this.handleActionChange = this.handleActionChange.bind(this);
        this.handleArgumentsChange = this.handleArgumentsChange.bind(this);
        this.handleKwargsChange = this.handleKwargsChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleClear = this.handleClear.bind(this);

        this.state = {
            loading: true,
            module: '',
            actions: [],
            selected: '',
            args: [],
            kwargs: {},
            status: undefined
        }
    }

    componentDidMount () {
        this.fetchExtension();
    }

    fetchExtension () {
        this.setState({
            loading: true,
        });

        fetch(`/api/obj/vendor?id=${this.props.vendorId}&getAttrs=ext_module&getAttrs=extension`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch extension information.')
        }).then(results => {
            this.setState({
                loading: false,
                module: results.items[0].ext_module,
                actions: results.items[0].extension,
            })
        }).catch(error => {
            alert(error);
            this.setState({
                loading: false,
                module: '',
                actions: []
            })
        })
    }

    sendExtAction (data) {
        console.log(data);
        fetch('/api/tasks', {
            body: JSON.stringify(data),
            headers: {
              'content-type': 'application/json'
            },
            method: 'POST'
        }).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Failed')
        }).then(results => {
            console.log(results)
        })
    }

    handleActionChange (e) {
        const newAction = e.target.value;
        this.setState(currentState => {
            return { selected: newAction }
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
        this.sendExtAction({
            module: this.state.module,
            action: this.state.selected,
            args: this.state.args,
            kwargs: this.state.kwargs
        });
    }

    handleClear () {
        this.setState({
            selected: '',
            args: [],
            kwargs: {}
        })
    }

    render () {
        return (
            <div className={"outlined"}>
                <h4>Extension: {this.state.loading ? 'Loading...' : this.state.module}</h4>
                {this.state.loading
                    ? ''
                    : <table>
                        <tbody>
                        <tr>
                            <td>
                                <div>
                                    <h6>Action</h6>
                                    <select value={this.state.selected} onChange={this.handleActionChange}>
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
                }
            </div>
        )
    }
}
