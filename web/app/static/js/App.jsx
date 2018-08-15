import React from "react";
import PropTypes from "prop-types";
import { Route, withRouter } from "react-router-dom";
import _ from "lodash";
import update from "immutability-helper";

import { Container, Segment, Menu, Search, Dropdown, Sidebar, Header, Button, Dimmer, Loader, Message, Grid } from "semantic-ui-react";

import Colander from "./colander";
import { DocumentContext, EditableDocProvider } from "./Context/DocumentContext";
import ObjectProperties from "./Objects/ObjectProperties";
import ObjectView from "./ObjectView";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const menuStyle = {
    borderRadius: 0,
    height: '5em'
};

const sidebarStyle = {
    backgroundColor: 'white',
    display: 'flex',
    flexDirection: 'column'
};

const sidebarHeaderStyle = update(menuStyle, {$merge: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center'
}});

const sidebarContentStyle = {
    flexGrow: 1,
    display: 'flex',
    flexFlow: 'column',
    padding: '1em',
    overflow: 'auto'
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


class CreatorSidebar extends React.Component {

    constructor (props) {
        super(props);

        this.fetchSchema = this.fetchSchema.bind(this);
        this.handleSave = this.handleSave.bind(this);
        this.handleCancel = this.handleCancel.bind(this);

        this.state = {
            loading: false,
            doc: {},
            schemas: {},
            errors: {}
        }
    }

    componentDidMount () { this.fetchSchema() }
    componentDidUpdate(prevProps) {
        if (prevProps.type !== this.props.type)
            this.fetchSchema();
    }

    fetchSchema () {
        this.setState({ loading: true });
        const { type } = this.props;

        Colander.schema(type, {
            onSuccess: results => this.setState({
                loading: false,
                schemas: results.definitions
            }),

            onFailure: results => this.setState({
                loading: false,
                schemas: {}
            })
        })
    }

    handleSave (edits) {
        const { doc } = this.state;
        const { onClose = () => {} } = this.props;

        this.setState({ loading: true });

        Colander.create(type, {
            data: update(doc, { $merge: edits }),

            onSuccess: results => {
                if (results.errors) {
                    this.setState({ loading: false, errors })
                } else {
                    this.setState({ loading: false, doc: {}, errors: {} });
                    onClose();
                }
            },

            onFailure: error => {
                this.setState({ loading: false, errors: { save: error } });
            }
        })
    }

    handleCancel () {
        const { onClose } = this.props;
        onClose && onClose();
    }

    render () {
        const { type, visible } = this.props;
        const { loading, errors } = this.state;

        const only = {
            Vendor: ['name', 'url', 'image_url', 'ext_id', 'avg_shipping', 'avg_tax'],
            Listing: ['vendor_id', 'sku', 'title', 'detail_url', 'image_url', 'brand', 'model', 'quantity', 'price', 'rank', 'rating'],
        }[type];

        return (
            <Sidebar
                direction={'right'}
                animation={'overlay'}
                width={'very wide'}
                visible={visible}
                style={sidebarStyle}
            >
                <EditableDocProvider {...this.state} type={type} onSave={this.handleSave}>
                    <Segment
                        inverted
                        color={'blue'}
                        textAlign={'center'}
                        style={sidebarHeaderStyle}
                    >
                        <Header as={'h2'}>Create {type}</Header>
                    </Segment>

                    <div style={sidebarContentStyle}>
                        <Dimmer.Dimmable dimmed={loading}>
                            <Dimmer active={loading}>
                                <Loader/>
                            </Dimmer>

                            <Grid>
                                <Grid.Row>
                                    <Grid.Column>
                                        <ObjectProperties as={'div'} only={only}/>
                                    </Grid.Column>
                                </Grid.Row>
                                <Grid.Row>
                                    <Grid.Column>
                                        <Message error hidden={_.isEmpty(errors)}>
                                            <DocumentContext.Consumer>
                                                { ({ errors }) => Object.keys(errors).map(err =>
                                                    <li key={err}>
                                                        <b>{err}</b>: {errors[err]}
                                                    </li>
                                                )}
                                            </DocumentContext.Consumer>
                                        </Message>
                                    </Grid.Column>
                                </Grid.Row>
                            </Grid>
                        </Dimmer.Dimmable>
                    </div>

                    <Segment
                        inverted
                        color={'blue'}
                        textAlign={'center'}
                        style={{borderRadius: 0}}
                    >
                        <DocumentContext.Consumer>
                            { ({ save }) => (
                                <React.Fragment>
                                    <Button onClick={this.handleCancel}>Cancel</Button>
                                    <Button onClick={save} loading={loading}>Create</Button>
                                </React.Fragment>
                            )}
                        </DocumentContext.Consumer>
                    </Segment>
                </EditableDocProvider>
            </Sidebar>
        )
    }
}


CreatorSidebar.propTypes = {
    type: PropTypes.string.isRequired,
    visible: PropTypes.bool
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


class App extends React.Component {

    constructor (props) {
        super(props);
        this.reset = this.reset.bind(this);
        this.handleQueryChange = this.handleQueryChange.bind(this);
        this.handleResultSelect = this.handleResultSelect.bind(this);
        this.hideSidebar = this.hideSidebar.bind(this);
        this.openCreator = this.openCreator.bind(this);
        this.fetchResults = _.debounce(this.fetchResults, 300, {trailing: true});

        this.state = {
            loading: false,
            results: [],
            query: '',
            sidebarVisible: false,
            creatorType: 'Vendor'
        }
    }

    reset () {
        this.setState({
            loading: false,
            results: [],
            query: ''
        })
    }

    fetchResults (query) {
        this.setState({ loading: true, query });

        Colander.preview({
            query,

            onSuccess: results => this.setState({ loading: false, results }),
            onFailure: error => { this.setState({ loading: false }); alert(error); }
        });
    }

    handleQueryChange (e, { value }) {
        if (!value)
            return this.reset();

        this.fetchResults(value);
    }

    handleResultSelect (e, data) {
        const url = `/${data.result.type}/${data.result.id}`;
        this.props.history.push(url);
    }

    hideSidebar () { this.setState({ sidebarVisible: false }) }
    openCreator (type) {
        this.setState({
            creatorType: type,
            sidebarVisible: true
        })
    }

    render () {
        const { loading, results, query, creatorType, sidebarVisible } = this.state;

        return (
            <Sidebar.Pushable>
                <CreatorSidebar
                    type={creatorType}
                    visible={sidebarVisible}
                    onCreated={id => alert(id)}
                    onCancel={this.hideSidebar}
                />
                <Sidebar.Pusher dimmed={sidebarVisible} onClick={() => this.setState({ sidebarVisible: false })}>
                    <Menu inverted style={menuStyle}>
                        <Menu.Item header>Colander</Menu.Item>
                        <Menu.Item>Dashboards</Menu.Item>
                        <Menu.Item>Search</Menu.Item>
                        <Menu.Item position={'right'}>
                            <Dropdown item text={'Create'}>
                                <Dropdown.Menu>
                                    <Dropdown.Item onClick={() => this.openCreator('Vendor')}>Vendor</Dropdown.Item>
                                    <Dropdown.Item onClick={() => this.openCreator('Customer')}>Customer</Dropdown.Item>
                                    <Dropdown.Item onClick={() => this.openCreator('Listing')}>Listing</Dropdown.Item>
                                    <Dropdown.Item onClick={() => this.openCreator('Task')}>Task</Dropdown.Item>
                                </Dropdown.Menu>
                            </Dropdown>
                        </Menu.Item>
                        <Menu.Item>
                            <Search
                                category
                                aligned={'right'}
                                loading={loading}
                                onSearchChange={this.handleQueryChange}
                                onResultSelect={this.handleResultSelect}
                                results={results}
                                value={query}
                            />
                        </Menu.Item>
                    </Menu>
                    <Container fluid style={{ paddingLeft: '5em', paddingRight: '5em'}}>
                        <Route path={'/:type/:id'} component={ObjectView}/>
                    </Container>
                </Sidebar.Pusher>
            </Sidebar.Pushable>
        );
    }
}

export default withRouter(App);