import React from "react";
import update from "immutability-helper";

import { Button } from "semantic-ui-react";

import Arguments from "./Arguments";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default class TaskView extends React.Component {

    constructor (props) {
        super(props);
        this.fetchTask = this.fetchTask.bind(this);
        this.fetchExtensions = this.fetchExtensions.bind(this);
        this.handleNameChange = this.handleNameChange.bind(this);
        this.handleExtChange = this.handleExtChange.bind(this);
        this.handleActionChange = this.handleActionChange.bind(this);
        this.handleParamsChange = this.handleParamsChange.bind(this);
        this.handleSave = this.handleSave.bind(this);
        this.handleCancel = this.handleCancel.bind(this);
        this.isValid = this.isValid.bind(this);

        this.state = {
            loading: true,
            task: {
                extension: {},
                params: {}
            },
            extensions: []
        }
    }

    componentDidMount () {
        if (this.props.match.params.taskId)
            this.fetchTask();
        else
            this.setState({ loading: false });

        this.fetchExtensions();
    }

    handleNameChange (e) {
        const value = e.target.value;
        this.setState(currentState => {
            return update(currentState, {
                task: {
                    name: {$set: value}
                }
            })
        } )
    }

    handleExtChange (e) {
        const extId = parseInt(e.target.value);
        const extName = e.target.text;

        this.setState(currentState => {
            return update(currentState, {
                task: {
                    ext_id: {$set: extId},
                    extension: {
                        id: {$set: extId},
                        name: {$set: extName}
                    }
                }
            })
        })
    }

    handleActionChange (e) {
        const action = e.target.value;

        this.setState(currentState => {
            return update(currentState, {
                task: {
                    action: { $set: action }
                }
            })
        })
    }

    handleParamsChange (data) {
        console.log(data);
        this.setState(currentState => {
            return update(currentState, {
                task: {
                    params: { $set: data }
                }
            })
        })
    }

    handleSave (e) {
        e.preventDefault();

        const url = '/api/obj/task';
        const body = {
            ids: [this.props.match.params.taskId],
            data: {
                name: this.state.task.name,
                ext_id: this.state.task.ext_id,
                action: this.state.task.action,
                params: this.state.task.params
            }
        };

        fetch(url, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify(body)
        }).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not saveObject changes.')
        }).then(results => {
            if (results.status !== 'ok')
                throw new Error(results.exception + ': ' + results.message)
        }).catch(error => {
            alert(error);

        }).finally(() => this.fetchTask())
    }

    handleCancel () {
        this.fetchTask();
    }

    fetchTask () {
        this.setState({ loading: true });

        const url = '/api/obj/task';
        const query = { id: this.props.match.params.taskId };
        const view = { extension: { _only: ['id', 'name'] } };

        const queryStr = encodeURIComponent(JSON.stringify(query));
        const viewStr = encodeURIComponent(JSON.stringify(view));

        fetch(`${url}?_query=${queryStr}&_view=${viewStr}`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch task.')
        }).then(results => {
            this.setState({
                loading: false,
                task: results.items[0]
            })
        }).catch(error => {
            alert(error);
            this.setState({ loading: false })
        })
    }

    fetchExtensions () {
        const url = '/api/obj/extension';
        const view = { _exclude: ['tasks'] };

        const viewStr = encodeURIComponent(JSON.stringify(view));

        fetch(`${url}?_view=${viewStr}`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch extensions.')
        }).then(results => {
            this.setState({
                extensions: results.items
            })
        }).catch(error => {
            alert(error);
        })
    }

    isValid () {
        return this.state.task && this.state.task.name && this.state.task.ext_id && this.state.task.action
    }

    render () {
        if (this.state.loading)
            return <div>Loading...</div>

        let extension = this.state.extensions.find(ext => ext.id === this.state.task.ext_id);

        return (
            <div>
                <ul>
                    <li>Name:
                        <input
                            type="text"
                            placeholder="Task name"
                            value={this.state.task.name}
                            onChange={this.handleNameChange}
                        />
                    </li>
                    <li>Extension:
                        <select value={this.state.task.ext_id} onChange={this.handleExtChange}>
                            {this.state.extensions.map(ext => {
                                return <option key={ext.id} value={ext.id}>{ext.name}</option>
                            })}
                        </select>
                    </li>
                    {!extension
                        ? 'Loading...'
                        : <li>Action:
                            <select value={this.state.task.action} onChange={this.handleActionChange}>
                                {Object.keys(extension.exports).map(ext => {
                                    return <option key={ext} value={ext}>{ext}</option>
                                })}
                            </select>
                        </li>
                    }
                    <li>Params: <Arguments data={this.state.task.params} onDataChanged={this.handleParamsChange}/></li>
                </ul>
                <Button onClick={this.handleSave} disabled={!this.isValid()}>Save</Button>
                <button>Cancel</button>
            </div>
        )
    }
}