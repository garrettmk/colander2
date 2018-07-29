import React from "react";
import PropTypes from "prop-types";
import update from "immutability-helper";
import { Segment, Popup, Header, Button, Table, Form, Select, Input, Icon, Search, Item, List, Grid,
Image, Dimmer, Message } from "semantic-ui-react";

import Colander from "./colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


class ListEditor extends React.Component {

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
        const { items=[], onChange } = this.props;
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
        const { items = []} = this.props;

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


ListEditor.propTypes = {
    items: PropTypes.array,
    onChange: PropTypes.func
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


class ObjectSelector extends React.Component {

    constructor (props) {
        super(props);

        this.handleQueryChange = this.handleQueryChange.bind(this);
        this.handleResultSelect = this.handleResultSelect.bind(this);
        this.fetchResults = this.fetchResults.bind(this);

        this.state = {
            query: '',
            loading: false,
            results: [],
            selected: {},
            searching: false,
        }
    }

    componentDidUpdate (prevProps, prevState) {
        if (prevState.query !== this.state.query
        && this.state.query)
            this.fetchResults();

        if (prevProps.value !== this.props.value)
            this.fetchObject();
    }

    handleQueryChange (e, { value }) {
        if (!value)
            return this.setState({ query: '', loading: false, results: [] });
        this.setState({ query: value });
    }

    handleResultSelect (e, { result }) {
        this.setState({ searching: false, selected: result });
    }

    fetchResults () {
        this.setState({ loading: true });

        const { type } = this.props;
        const { query } = this.state;

        Colander.quick({
            types: [type],
            query,

            onSuccess: results => this.setState({ loading: false, results: results[type].results }),
            onFailure: error => this.setState({ loading: false })
        })
    }

    fetchObject () {
        this.setState({ loading: true });
        const { type, value } = this.props;

        Colander.filter(type, {
            query: { id: value },
            view: { _schema: 'Preview'},

            onSuccess: results => this.setState({ loading: false, selected: results.items ? results.items[0] : {} }),
            onFailure: error => this.setState({ loading: false, selected: {} })
        })
    }

    render () {
        const { type, ...childProps } = this.props;
        const { loading, query, results, searching, selected } = this.state;
        const defaultImage = 'https://imgplaceholder.com/420x320/cccccc/757575/fa-question';
        const imageUrl = searching ? defaultImage : selected.image || defaultImage;

        return (
            <Table basic={'very'} style={{ tableLayout: 'fixed', width: '100%' }}>
                <Table.Body>
                    <Table.Row>
                        <Table.Cell style={{ width: '80px' }}>
                            <Image size={'tiny'} src={imageUrl}/>
                        </Table.Cell>
                        <Table.Cell rowSpan={2} singleline>
                            {searching
                                ? <Search
                                    fluid
                                    icon={null}
                                    loading={loading}
                                    onSearchChange={this.handleQueryChange}
                                    onResultSelect={this.handleResultSelect}
                                    results={results}
                                    value={query}
                                    {...childProps}
                                />

                                : <React.Fragment>
                                    <Header size={'tiny'} style={{ overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                                        { selected.title }
                                    </Header>
                                    {selected.description}
                                </React.Fragment>
                            }
                        </Table.Cell>
                        <Table.Cell style={{ width: '4em' }}>
                            <Button
                                icon={'search'}
                                onClick={() => this.setState({ searching: !this.state.searching })}
                            />
                        </Table.Cell>
                    </Table.Row>
                </Table.Body>
            </Table>
        );
    }
}


ObjectSelector.propTypes = {
    type: PropTypes.string.isRequired,
    value: PropTypes.number,
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function Control (props) {
    const { schema, required, onChange, value, error } = props;
    const handleChange = onChange ? (v) => onChange(v) : undefined;

    if (schema.idtype)
        return <ObjectSelector
            type={schema.idtype}
            onChange={handleChange}
            value={value}
            error
        />;

    switch (schema.type) {
        case 'array':
            return <ListEditor
                items={value}
                onChange={handleChange}
                error
            />;

        case 'object':
            return <pre>{value ? JSON.stringify(value, null, '  ') : '(none)'}</pre>;

        case 'number':
        case 'string':
            const format = {
                type: {
                    string: 'text',
                    integer: 'number',
                    float: 'number'
                }[schema.format || 'string'],
                step: {
                    integer: '1',
                    float: '0.01'
                }[schema.format || 'string']
            };

            return <Input
                placeholder={schema.name || schema.title}
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
}


Control.propTypes = {
    schema: PropTypes.object.isRequired,
    required: PropTypes.bool,
    onChange: PropTypes.func,
    value: PropTypes.any,
    error: PropTypes.bool
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default function Autoform (props) {

    const { schema, data, onChange, tablerows, only, exclude } = props;
    const { properties = {}, required = [] } = schema;
    const keys = only ? only : Object.keys(properties).filter(key => !exclude.includes(key));
    const fields = keys.map(key => ({
        key: key,
        schema: properties[key],
        value: data[key]
    }));

    const handleChange = field => (
        onChange
            ? value => onChange(update(data, { [field]: {$set: value} }))
            : undefined
    );

    const rows = fields.map(({ key, schema = {}, value }) => (
            <Table.Row key={key}>
                <Table.Cell>
                    <Header size={'tiny'}>
                        {schema.name || schema.title || schema.field}
                    </Header>
                </Table.Cell>
                <Table.Cell>
                    <Control
                        schema={schema}
                        value={value}
                        onChange={handleChange(key)}
                    />
                </Table.Cell>
            </Table.Row>
    ));

    if (tablerows)
        return <React.Fragment>{rows}</React.Fragment>;
    else
        return (
            <Table basic={'very'}>
                <Table.Body>
                    {rows}
                </Table.Body>
            </Table>
        );
}


Autoform.propTypes = {
    schema: PropTypes.object.isRequired,
    data: PropTypes.object.isRequired,
    onChange: PropTypes.func,
    error: PropTypes.object,
    only: PropTypes.arrayOf(PropTypes.string),
    exclude: PropTypes.arrayOf(PropTypes.string)
};

Autoform.defaultProps = {
    exclude: []
};