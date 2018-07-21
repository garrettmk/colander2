import React from "react";
import Arguments from "./Arguments";


export default class Extension extends React.Component {

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
            ext: {},
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
        this.setState({ loading: true, });

        const url = '/api/obj/extension';
        const query = { id: this.props.id };
        const view = { tasks: { _exclude: ['ext_id', 'extension'] } };

        const queryString = encodeURIComponent(JSON.stringify(query));
        const viewString = encodeURIComponent(JSON.stringify(view));

        fetch(`${url}?_query=${queryString}&_view=${viewString}`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch extension information.')
        }).then(results => {

            this.setState({
                loading: false,
                ext: results.items[0] || { exports: {} },
                selected: results.items[0] ? Object.keys(results.items[0].exports)[0] : ''
            })
        }).catch(error => {
            alert(error);
            this.setState({
                loading: false,
            })
        })
    }

    sendExtAction (data) {
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
        console.log(e);
        const newAction = e.target.value;
        this.setState({ selected: newAction });
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
            module: this.state.ext.module,
            action: this.state.selected,
            params: {
                args: this.state.args,
                kwargs: this.state.kwargs
            }
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
                <h4>Extension</h4>
                {this.state.loading
                    ? 'Loading...'
                    : <div>
                        <ul>
                            <li>Name: {this.state.ext.name}</li>
                            <li>Module: {this.state.ext.module}</li>
                        </ul>
                        <ul>
                            <li>
                                Action: <select value={this.state.selected} onChange={this.handleActionChange}>
                                            {Object.keys(this.state.ext.exports).map(action => {
                                                console.log(action);
                                                return <option key={action} value={action}>{action}</option>
                                            })}
                                        </select>
                            </li>
                            <li>
                                Arguments: <Arguments data={this.state.args} onDataChanged={this.handleArgumentsChange}/>
                            </li>
                            <li>
                                Parameters: <Arguments data={this.state.kwargs} onDataChanged={this.handleKwargsChange}/>
                            </li>
                        </ul>
                        <div>
                            <button onClick={this.handleSubmit}>Send</button>
                            <button onClick={this.handleClear}>Clear</button>
                        </div>
                    </div>
                }
            </div>
        )
    }
}
