import React from "react";
import update from "immutability-helper";
import { List, Grid, Segment, Header, Form, Button } from "semantic-ui-react";

import Colander from "./colander";
import EntityDetails from "./ObjectDetails";
import { ActionSelector} from "./Selectors";
import { JSONInput } from "./Forms";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function ExtensionDetails (props) {
    const { id } = props;
    return (
        <EntityDetails
            type={'extension'}
            id={id}
            strict
            extra
            format={{
                name: ext => ({ label: "Name", value: ext.name }),
                module: ext => ({ label: "Module", value: ext.module }),
                exports: ext => ({ label: "Exports", value: ext.exports ? <List items={Object.keys(ext.exports)}/> : '(none)'})
            }}
        />
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


class ActionSender extends React.Component {

    constructor (props) {
        super(props);

        this.handleChange = this.handleChange.bind(this);
        this.handleSend = this.handleSend.bind(this);

        this.state = {
            task: {
                ext_id: parseInt(props.extId)
            },
            errors: {},
            sending: false
        }
    }

    handleChange (e, { name, value }) {
        this.setState(current => update(current, { task: { [name]: {$set: value} }}))
    }

    handleSend () {
        const { task } = this.state;

        this.setState({ sending: true });

        Colander.sendTask({
            ...task,

            onSuccess: results => {
                console.log(results);
                this.setState({ sending: false });
            },

            onFailure: error => {
                alert(error);
                this.setState({ sending: false });
            }
        })
    }

    render () {
        const { extId } = this.props;
        const { task, errors, sending } = this.state;
        const ready = task.action && !sending;

        return (
            <Segment raised clearing>
                <Header size={'medium'} dividing>Send Action</Header>
                <Form>
                    <ActionSelector
                        form
                        label={'Action'}
                        extId={extId}
                        value={task.action}
                        placeholder={'Action'}
                        name={'action'}
                        onChange={this.handleChange}
                        error={'action' in errors}
                    />
                    <JSONInput
                        form
                        rows={8}
                        label={'Parameters'}
                        value={task.params}
                        placeholder={'{\n\t"args": {},\n\t"kwargs": {}\n}'}
                        name={'params'}
                        onChange={this.handleChange}
                        error={'params' in errors}
                    />
                </Form>
                <Button
                    color={'blue'}
                    floated={'right'}
                    loading={sending}
                    disabled={!ready}
                    onClick={this.handleSend}
                >
                    Send
                </Button>
            </Segment>
        )
    }
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default function ExtensionView (props) {
    const { extId } = props.match.params;
    console.log(extId)

    return (
        <Grid columns={2}>
            <Grid.Column width={6}>
                <ExtensionDetails id={extId}/>
                <ActionSender extId={extId}/>
            </Grid.Column>
            <Grid.Column width={10}>

            </Grid.Column>
        </Grid>
    )
}