import React from "react";
import { Route, Link, withRouter } from "react-router-dom";
import queryString from "query-string";
import _ from "lodash";
import update from "immutability-helper";

import Colander from "./colander";

import {
    Container,
    Segment,
    Menu,
    Search,
    Dropdown,
    Sidebar,
    Header,
    Button,
    Dimmer,
    Message,
    Grid
} from "semantic-ui-react";

import forms from "./Forms";

// import DashboardView from "./DashboardView";
// import SearchView from "./SearchView";
// import VendorView from "./VendorView";
// import ListingView from "./ListingView";
// import OrderView from "./OrderView";
// import ExtensionView from "./ExtensionView";
// import TaskView from "./TaskView";
import ObjectView from "./ObjectView";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function asCurrency(value) {
    try {
        if (typeof value === 'string')
            value = parseFloat(value);

        return value.toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD'
        })
    } catch (e) {
        return 'n/a'
    }
}

export function asCount(value) {
        try {
            if (typeof value === 'string')
                value = parseInt(value)
            return value.toLocaleString('en-US');
        } catch (e) {
            return 'n/a'
        }

}

export function asPercent(value) {
    try {
        if (typeof value === 'string')
            value = parseFloat(value);
        return (value * 100).toLocaleString('en-US') + '%'
    } catch (e) {
        return 'n/a'
    }
}


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

        this.handleEdit = this.handleEdit.bind(this);
        this.handleCancel = this.handleCancel.bind(this);
        this.handleCreate = this.handleCreate.bind(this);

        this.state = {
            creating: false,
            object: {},
            errors: {}
        }
    }

    handleEdit (e, { name, value }) {
        this.setState({ object: update(this.state.object, { [name]: { $set: value } })});
    }

    handleCancel () {
        const { onCancel } = this.props;
        onCancel ? onCancel() : null;
    }

    handleCreate () {
        this.setState({ creating: true });
        const { type, onCreated } = this.props;

        Colander.create(type, {
            data: this.state.object,

            onSuccess: results => {
                if ('errors' in results)
                    this.setState({
                        creating: false,
                        errors: results.errors
                    });
                else {
                    this.setState({ creating: false });
                    onCreated ? onCreated(results.id) : null;
                }
            },

            onFailure: error => {
                this.setState({ creating: false });
                alert(error);
            }
        });
    }

    render () {
        const { creating, object, errors } = this.state;
        const { type, visible } = this.props;
        const form = forms[type]({ data: object, onChange: this.handleEdit, errors});

        return (
            <Sidebar
                direction={'right'}
                animation={'overlay'}
                width={'very wide'}
                visible={visible}
                style={sidebarStyle}
            >
                <Segment
                    inverted
                    color={'blue'}
                    textAlign={'center'}
                    style={sidebarHeaderStyle}
                >
                    <Header as={'h2'}>Create {_.capitalize(type)}</Header>
                </Segment>
                <div style={sidebarContentStyle}>
                    <Grid columns={1}>
                        <Grid.Row>
                            <Grid.Column>
                                {form}
                            </Grid.Column>
                        </Grid.Row>
                        <Grid.Row>
                            <Grid.Column>
                                <Message error hidden={_.isEmpty(errors)}>
                                    {Object.keys(errors).map(err => <li key={err}><b>{err}</b>: {errors[err]}</li>)}
                                </Message>
                            </Grid.Column>
                        </Grid.Row>
                    </Grid>
                </div>
                <Segment
                    inverted
                    color={'blue'}
                    textAlign={'center'}
                    style={{ borderRadius: 0 }}
                >
                    <Button onClick={this.handleCancel}>Cancel</Button>
                    <Button onClick={this.handleCreate} loading={creating}>Create</Button>
                </Segment>
            </Sidebar>
        )
    }
}


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
            creatorType: 'vendor'
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
        fetch(`/api/quick?query=${query}`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch search results.')
        }).then(results => {
            this.setState({
                loading: false,
                results
            })
        }).catch(error => {
            alert(error);
            this.reset();
        })
    }

    handleQueryChange (e, { value }) {
        if (!value)
            return this.reset();

        this.setState({ loading: true, query: value });
        this.fetchResults(value);
    }

    handleResultSelect (e, data) {
        const url = `/${data.result.type.toLowerCase()}s/${data.result.id}`;
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
        const query = queryString.parse(location.search);
        const { creatorType, sidebarVisible } = this.state;

        return (
            <Sidebar.Pushable>
                <CreatorSidebar
                    type={creatorType}
                    visible={sidebarVisible}
                    onCreated={id => alert(id)}
                    onCancel={this.hideSidebar}
                />
                <Sidebar.Pusher dimmed={this.state.sidebarVisible} onClick={() => this.setState({sidebarVisible: false})}>
                    <Menu inverted style={menuStyle}>
                        <Menu.Item header>Colander</Menu.Item>
                        <Menu.Item>Dashboards</Menu.Item>
                        <Menu.Item>Search</Menu.Item>
                        <Menu.Item position={'right'}>
                            <Dropdown item text={'Create'}>
                                <Dropdown.Menu>
                                    <Dropdown.Item onClick={() => this.openCreator('vendor')}>Vendor</Dropdown.Item>
                                    <Dropdown.Item onClick={() => this.openCreator('customer')}>Customer</Dropdown.Item>
                                    <Dropdown.Item onClick={() => this.openCreator('listing')}>Listing</Dropdown.Item>
                                    <Dropdown.Item onClick={() => {this.openCreator('task')}}>Task</Dropdown.Item>
                                </Dropdown.Menu>
                            </Dropdown>
                        </Menu.Item>
                        <Menu.Item>
                            <Search
                                category
                                aligned={'right'}
                                loading={this.state.loading}
                                onSearchChange={this.handleQueryChange}
                                onResultSelect={this.handleResultSelect}
                                results={this.state.results}
                                value={this.state.query}
                            />
                        </Menu.Item>
                    </Menu>
                    <Container fluid style={{ paddingLeft: '5em', paddingRight: '5em'}}>
                        <Route path={'/:type/:id'} component={ObjectView}/>


                        {/*/!*<Route exact path={'/'} component={DashboardView}/>*!/*/}
                        {/*/!*<Route path={'/search'} component={SearchView}/>*!/*/}
                        {/*<Route path={'/vendors/:vendorId'} component={VendorView}/>*/}
                        {/*<Route path={'/listings/:listingId'} component={ListingView}/>*/}
                        {/*/!*<Route path={'/orders/:orderId'} component={OrderView}/>*!/*/}
                        {/*<Route path={'/extensions/:extId'} component={ExtensionView}/>*/}
                        {/*/!*<Route path={'/tasks/:taskId(\\d+)'} component={TaskView}/>*!/*/}
                        {/*/!*<Route path={'/tasks/create'} component={TaskView}/>*!/*/}
                    </Container>
                </Sidebar.Pusher>
            </Sidebar.Pushable>
        );
    }
}

export default withRouter(App);