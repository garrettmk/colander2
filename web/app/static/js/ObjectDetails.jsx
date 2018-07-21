import React from "react";
import _ from "lodash";
import Colander from "./colander";

import { Segment, Header, Image, Message, Table, Button, Popup, Icon, Dimmer, Loader, Grid, Divider, Form } from "semantic-ui-react";
import forms from "./Forms";
import update from "immutability-helper/index";


const defaultImages = {
    vendor: 'https://imgplaceholder.com/128x128/cccccc/757575/fa-globe',
    customer: 'https://imgplaceholder.com/128x128/cccccc/757575/ion-android-person',
    extension: 'https://imgplaceholder.com/128x128/cccccc/757575/fa-gears'
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function ExtraPopup (props) {
    const { data } = props;
    return (
        <Popup trigger={<span>...</span>}>
            <pre>{JSON.stringify(data, null, '  ')}</pre>
        </Popup>
    )
}

function TitlePopup (props) {
    const { header, subheader } = props;
    const headerOpts = {
            dividing: true,
            style: {
                whiteSpace: 'nowrap',
                textOverflow: 'ellipsis',
                overflow: 'hidden',
                display: 'block',
            }
        };

    const trigger = (
        <Header {...headerOpts}>
            {header}
            <Header.Subheader>
                {subheader}
            </Header.Subheader>
        </Header>
    );

    return (
        <Popup trigger={trigger}>
            <Header>
                {header}
                <Header.Subheader>
                    {subheader}
                </Header.Subheader>
            </Header>
        </Popup>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default class ObjectDetails extends React.Component {

    constructor (props) {
        super(props);

        this.fetchObject = this.fetchObject.bind(this);
        this.toggleEditor = this.toggleEditor.bind(this);
        this.handleSave = this.handleSave.bind(this);
        this.handleEdit = this.handleEdit.bind(this);
        this.handleCancelEdit = this.handleCancelEdit.bind(this);

        this.state = {
            loading: true,
            editing: false,
            object: {},
            edits: {},
            errors: {}
        }
    }

    componentDidMount () { this.fetchObject(); }
    toggleEditor () { this.setState(current => {return { editing: !current.editing }}) }
    handleCancelEdit () { this.setState({ editing: false, edits: {} }) }
    handleEdit (e, { name, value }) {
        this.setState(current => update(current, { edits: { [name]: {$set: value} }})) }

    fetchObject () {
        this.setState({ loading: true });
        const { type, id, view = {} } = this.props;

        Colander.filter(type, {
            query: { id },
            view,

            onSuccess: results => { this.setState({ loading: false, object: results.items[0], edits: {} }) },
            onFailure: error => { this.setState({ loading: false, errors: { fetch: error }}) }
        })
    }

    handleSave () {
        this.setState({ loading: true });
        const { type, id } = this.props;
        const { object, edits } = this.state;

        Colander.update(type, {
            data: edits,
            query: { id },

            onSuccess: results => {
                if ('errors' in results)
                    this.setState({
                        loading: false,
                        errors: results.errors
                    });
                else {
                    this.setState({
                        loading: false,
                        object: update(object, {$merge: edits}),
                        editing: false
                    });
                }
            },

            onFailure: error => {
                this.setState({ loading: false, errors: { fetch: error } });
            }
        })
    }


    render () {
        const { type, strict, extra } = this.props;
        const { loading, editing, errors, object, edits } = this.state;
        const form = forms[type]({ data: update(object, {$merge: edits}), onChange: this.handleEdit, errors });

        const {
            _header = obj => obj.name || obj.title,
            _subheader = obj => {
                const url = obj.url || obj.email || obj.detail_url;
                return <a target="blank" href={url}>{url}</a>;
            },
            _image = obj => obj.image_url,
            _url = obj => obj.url || obj.email || obj.detail_url,
            ...attrFormats
        } = this.props.format;

        if (extra)
            attrFormats.extra = obj => ({ label: 'Extra', value: <ExtraPopup data={obj.extra}/>});

        const attrKeys = Object.keys(strict ? attrFormats : object);

        const editButtonOpts = {
            compact: true,
            circular: true,
            color: 'blue',
            icon: 'edit',
            basic: !editing,
            onClick: this.toggleEditor,
            style: {
                position: 'absolute',
                top: 0,
                right: 0
            }
        };

        const headerImgOpts = {
            size: 'small',
            src: _image(object),
            href: _url(object),
            centered: true,
            rounded: true,
            style: {
                display: 'block'
            }
        };

        if (errors.fetch)
            return (
                <Segment raised>
                    <Message error>{errors.fetch}</Message>
                </Segment>
            );
        else
            return (
                <Segment raised clearing loading={loading}>
                    <div style={{ position: 'relative' }}>
                        <Image {...headerImgOpts}/>
                        <Button {...editButtonOpts}/>
                    </div>
                    <TitlePopup
                        header={_header(object)}
                        subheader={_subheader(object)}
                    />

                    {editing
                        ? <div style={{ paddingTop: '1em' }}>
                            {form}
                            <Message error hidden={_.isEmpty(errors)}>
                                {Object.keys(errors).map(err => <li key={err}><b>{err}</b>: {errors[err]}</li>)}
                            </Message>
                            <Button.Group fluid style={{ marginTop: '2em' }}>
                                <Button onClick={this.handleCancelEdit}>Cancel</Button>
                                <Button.Or />
                                <Button onClick={this.handleSave} color={'blue'}>Save</Button>
                            </Button.Group>
                        </div>

                        : <Table basic={'very'}>
                            <Table.Body>
                                {attrKeys.map(attr => {
                                    const { label, value } = attr in attrFormats
                                                                ? attrFormats[attr](object)
                                                                : { label: attr, value: object[attr] };
                                    return <Table.Row key={attr}>
                                        <Table.Cell>
                                            <Header size={'tiny'}>
                                                {label}
                                            </Header>
                                        </Table.Cell>
                                        <Table.Cell>
                                            {value}
                                        </Table.Cell>
                                    </Table.Row>
                                })}
                            </Table.Body>
                        </Table>
                    }
                </Segment>
            )
    }
}
