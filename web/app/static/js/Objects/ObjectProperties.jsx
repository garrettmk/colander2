import React from "react";
import { Segment, Table, Header, Message, Icon, Input } from "semantic-ui-react";

import { DocumentContext } from "../Context/DocumentContext";
import { PreviewProvider } from "../Context/PreviewProvider";
import ObjectPreview from "./ObjectPreview";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function FieldLabel (props) {
    const { field } = props;

    return (
        <DocumentContext.Consumer>
            { ({ schemas, type }) => {
                const schema = schemas[type].properties[field];
                const label = schema.label || schema.title || schema.name || field;

                let format;
                switch (schema.format) {
                    case 'percent':
                        format = '%';
                        break;
                }

                return format ? `${label} (${format})` : label;
            }}
        </DocumentContext.Consumer>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function Field (props) {
    const { field, onChange } = props;
    const handleChange = onChange ? (v) => onChange(v) : undefined;

    return (
        <DocumentContext.Consumer>
            { ({ schemas, type, original, edited, errors }) => {
                const schema = schemas[type].properties[field];

                const label = schema.label || schema.title || schema.name || schema.field || field;
                const value = onChange ? edited[field] : original[field];
                const error = errors ? errors[field] : undefined;

                if (schema.idtype)
                    return (
                        <PreviewProvider type={schema.idtype} id={value}>
                            <ObjectPreview small onChange={handleChange}/>
                        </PreviewProvider>
                    );

                switch (schema.type) {
                    case 'array':
                        return <ListEditor field={value} onChange={handleChange}/>;

                    case 'object':
                        return <pre>{value ? JSON.stringify(value, null, '  ') : '(none)'}</pre>;

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
                            value={value}
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


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default function ObjectProperties (props) {
    let { as, only, exclude = [], ...containerProps } = props;

    if (!as) {
        as = Segment;
        if (containerProps.raised === undefined)
            containerProps.raised = true
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
                        <Table basic={'very'}>
                            <Table.Body>
                                {fields.map(field => (
                                    <Table.Row key={field} style={{ borderBottom: '2px gray' }}>
                                        <Table.Cell>
                                            <Header size={'tiny'}>
                                                <FieldLabel field={field}/>
                                            </Header>
                                        </Table.Cell>
                                        <Table.Cell>
                                            <Field field={field} onChange={edit ? value => edit(field, value) : undefined}/>
                                        </Table.Cell>
                                    </Table.Row>
                                ))}
                            </Table.Body>
                        </Table>
                    )
                }

                return React.createElement(as, containerProps, children);
            }}
        </DocumentContext.Consumer>
    )
}

