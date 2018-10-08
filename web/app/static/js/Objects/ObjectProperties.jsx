import React from "react";
import PropTypes from "prop-types";
import { Segment, Table, Header, Message, Icon, Input, List, TextArea } from "semantic-ui-react";

import { DocumentContext, PreviewProvider } from "../Contexts";
import { ObjectPreview } from "./ObjectPreview";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function FieldLabel (props) {
    const { field } = props;

    return (
        <DocumentContext.Consumer>
            { ({ schemas, type }) => {
                if (!schemas || !type)
                    return '';

                const schema = schemas[type].properties[field];
                const label = schema ? schema.label || schema.title || schema.name || field : field;

                let format;
                switch (schema && schema.format) {
                    case 'percent':
                        format = '%';
                        break;
                }

                return format ? `${label} (${format})` : label;
            }}
        </DocumentContext.Consumer>
    )
}


FieldLabel.propTypes = {
    field: PropTypes.string.isRequired
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function Field (props) {
    const { field, onChange } = props;
    const handleChange = onChange ? (v) => onChange(v) : undefined;

    return (
        <DocumentContext.Consumer>
            { ({ schemas, type, doc, edited, errors }) => {
                if (!schemas || !type || !doc || !edited)
                    return <React.Fragment/>;

                const schema = schemas[type].properties[field];

                const label = schema ? schema.label || schema.title || schema.name || schema.field || field : field;
                const value = onChange ? edited[field] : doc[field];
                const error = errors ? errors[field] : undefined;

                if (schema && schema.idtype)
                    return (
                        <PreviewProvider type={schema.idtype} id={value}>
                            <ObjectPreview small onChange={handleChange}/>
                        </PreviewProvider>
                    );

                switch (schema && schema.type) {
                    case undefined:
                        return <React.Fragment/>;

                    case 'array':
                        return <ListField items={value} onChange={handleChange}/>;

                    case 'object':
                        return <JsonField json={value} onChange={handleChange}/>;

                    case 'number':
                    case 'string':

                        let format = {};
                        switch (schema.format) {

                            case 'string':
                                format.type = 'text';
                                break;

                            case 'url':
                                format.type = 'text';
                                format.icon = <Icon name={'globe'} link onClick={() => window.open(value, '_blank')}/>;
                                format.iconPosition = 'left';
                                break;

                            case 'email':
                                format.type = 'text';
                                format.icon = 'at';
                                format.iconPosition = 'left';
                                break;

                            case 'integer':
                                format.type = 'number';
                                format.step = '1';
                                break;

                            case 'float':
                                format.type = 'number';
                                format.step = '0.01';
                                format.icon = 'dollar';
                                format.iconPosition = 'left';
                                break;

                            case 'percent':
                                format.type = 'number';
                                format.step = '0.1';
                                format.icon = 'percent';
                                break;
                        }

                        return <Input
                            fluid
                            placeholder={label}
                            error={error}
                            value={value || ''}
                            transparent
                            disabled={!onChange}
                            onChange={(e, { value }) => handleChange(value)}
                            {...format}
                        />;

                    default:
                        return <Message
                            error
                            content={'Unrecognized field type: ' + schema.type}
                        />;
                }
            }}
        </DocumentContext.Consumer>
    )
}


Field.propTypes = {
    field: PropTypes.string.isRequired,
    onChange: PropTypes.func
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


class ListField extends React.Component {

    constructor (props) {
        super(props);

        this.handleInputChange = this.handleInputChange.bind(this);
        this.handleAdd = this.handleAdd.bind(this);
        this.handleRemove = this.handleRemove.bind(this);

        this.state = {
            input: ''
        }
    }

    handleInputChange (e, { value }) {
        this.setState({ input: value });
    }

    handleAdd () {
        const { items, onChange } = this.props;
        if (onChange) {
            onChange(items.concat([this.state.input]))
        }
    }

    handleRemove (index) {
        return () => {
            const { items, onChange } = this.props;
            if (onChange) {
                onChange(items.filter((item, idx) => idx !== index))
            }
        }
    }

    handleEdit (index) {
        return (e, { value} ) => {
            const { items, onChange } = this.props;
            if (onChange)
                onChange(update(items, {[index]: {$set: value}}))
        }
    }

    render () {
        const { items } = this.props;

        return (
            <div>
                <Input
                    action={{ icon: 'plus', onClick: this.handleAdd }}
                    placeholder={'http:/www.acme.com'}
                    value={this.state.value}
                    onChange={this.handleInputChange}
                    fluid
                />
                <List>
                    {items.map((item, idx) => (
                        <List.Item key={idx}>
                            <Input
                                icon={'globe'}
                                iconPosition={'left'}
                                value={item}
                                onChange={this.handleEdit(idx)}
                                fluid
                                transparent
                                action={{ icon: 'delete', onClick: this.handleRemove(idx), style: { backgroundColor: 'transparent' }}}
                            />
                        </List.Item>
                    ))}
                </List>
            </div>
        )
    }
}


ListField.propTypes = {
    items: PropTypes.array,
    onChange: PropTypes.func
};


ListField.defaultProps = {
    items: []
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class JsonField extends React.Component {

    constructor (props) {
        super(props);

        this.tryToParse = this.tryToParse.bind(this);
        this.convertToText = this.convertToText.bind(this);

        this.state = { text: '' }
    }

    componentDidMount () {
        this.convertToText();
    }

    componentDidUpdate (prevProps, prevState) {
        if (prevState.text !== this.state.text)
            this.tryToParse();

        else if (!_.isEqual(prevProps.json, this.props.json))
            this.convertToText();
    }

    convertToText () {
        const { json } = this.props;
        if (json)
            this.setState({ text: JSON.stringify(json, null, '  ') });
        else
            this.setState({ text: '' });
    }

    tryToParse () {
        const { text } = this.state;
        const { onChange } = this.props;

        if (!onChange)
            return;

        try {
            const json = text ? JSON.parse(text) : undefined;
            if (!_.isEqual(json, this.props.json))
                onChange(json)
        } catch (error) { }
    }

    render () {
        const { text } = this.state;
        const rows = Math.min(text.split('\n').length, 8);

        return (
            <TextArea
                rows={rows}
                value={text}
                placeholder={'no data'}
                onChange={(e, { value }) => this.setState({ text: value })}
                style={{
                    width: '100%',
                    border: 'none',
                    resize: 'vertical'
                }}
            />
        )
    }
}


JsonField.propTypes = {
    json: PropTypes.object,
    onChange: PropTypes.func
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function ObjectProperties (props) {
    let { as, only, exclude, ...containerProps } = props;

    if (!as) {
        as = Segment;
        if (containerProps.raised === undefined)
            containerProps.raised = true;
    }

    return (
        <DocumentContext.Consumer>
            { ({ loading, edited, schemas, type, edit }) => {

                let children;
                if (loading || !schemas[type]) {
                    children = <React.Fragment/>;
                } else {
                    const { properties = {}, required = [] } = schemas ? schemas[type] : {};
                    const fields = (only || Object.keys(properties)).filter(key => !exclude.includes(key));

                    children = (
                        <React.Fragment>
                            {fields.map(field => (
                                <div key={field} style={{ display: 'flex', flexDirection: 'column', borderBottom: '1px dotted lightgrey', marginBottom: '1em', paddingBottom: '0.3em' }}>
                                    <Header sub size={'tiny'} color={'grey'} style={{ margin: 0, marginBottom: '0.3em' }}>
                                        <FieldLabel field={field}/>
                                    </Header>
                                    <Field field={field} onChange={edit ? value => edit(field, value) : undefined}/>
                                </div>
                            ))}
                        </React.Fragment>
                    )
                }

                return React.createElement(as, containerProps, children);
            }}
        </DocumentContext.Consumer>
    )
}


ObjectProperties.propTypes = {
    as: PropTypes.oneOfType([PropTypes.string, PropTypes.func]),
    only: PropTypes.arrayOf(PropTypes.string),
    exclude: PropTypes.arrayOf(PropTypes.string)
};


ObjectProperties.defaultProps = {
    exclude: []
};